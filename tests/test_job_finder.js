"use strict";

const assert = require("node:assert/strict");
const {
  CACHE_TTL,
  cleanText,
  loadJobs,
  normalizeJob,
  prepareJobs,
  scoreJob,
} = require("../job_finder.js");

const baseJob = {
  id: 101,
  title: "Senior Product Designer",
  company_name: "Example Studio",
  url: "https://remotive.com/remote-jobs/design/senior-product-designer-101",
  publication_date: "2026-10-17T10:00:00Z",
  candidate_required_location: "Worldwide",
  category: "Design",
  tags: ["Figma", "research"],
  description: "<p>Lead product design and user research with Figma.</p>",
};

function testNormalizationRejectsUnverifiableLinksAndStripsMarkup() {
  assert.equal(normalizeJob({ ...baseJob, url: "javascript:alert(1)" }), null);
  assert.equal(normalizeJob({ ...baseJob, url: "https://example.com/job" }), null);
  assert.equal(normalizeJob({ ...baseJob, url: "https://remotive.com/not-a-job" }), null);
  assert.equal(normalizeJob({ ...baseJob, publication_date: "" }), null);
  assert.equal(cleanText("<p>Product&nbsp;design &amp; research</p>"), "Product design & research");
  assert.equal(normalizeJob(baseJob).description, "Lead product design and user research with Figma.");
  const fullDescription = normalizeJob({ ...baseJob, description: `<p>${"x".repeat(6000)}</p>` });
  assert.equal(fullDescription.description.length, 6000);
  assert.equal(fullDescription.descriptionTruncated, false);
  const longDescription = normalizeJob({ ...baseJob, description: `<p>${"x".repeat(13000)}</p>` });
  assert.equal(longDescription.description.length, 12000);
  assert.equal(longDescription.descriptionTruncated, true);
  const legacyDescription = normalizeJob({ ...baseJob, description: "x".repeat(1400) });
  assert.equal(legacyDescription.descriptionTruncated, true);
}

function testMatchingExplainsSkillsLocationAndFreshness() {
  const profile = { role: "Product Designer", skills: "Figma, user research", location: "Singapore" };
  const result = scoreJob(normalizeJob(baseJob), profile, Date.parse("2026-10-18T00:00:00Z"));
  assert.deepEqual(result.matchedSkills, ["figma", "user research"]);
  assert.equal(result.locationMatches, true);
  assert.equal(result.breakdown.find((part) => part.label === "发布时间").score, 100);
  assert.ok(result.score >= 90);
}

function testPreparationDeduplicatesAndUsesSourceOnlyRecords() {
  const jobs = prepareJobs([baseJob, baseJob, { ...baseJob, url: "https://fake.example/role" }], {
    role: "Product Designer",
    skills: "",
    location: "",
  }, Date.parse("2026-10-18T00:00:00Z"));
  assert.equal(jobs.length, 1);
  assert.equal(jobs[0].company, "Example Studio");
  assert.ok(jobs[0].match.score >= 80);
}

function testTitleMatchesRankAboveDescriptionMentions() {
  const profile = { role: "React", skills: "", location: "" };
  const now = Date.parse("2026-10-18T00:00:00Z");
  const titleMatch = scoreJob(normalizeJob({ ...baseJob, title: "React Engineer", description: "" }), profile, now);
  const descriptionOnly = scoreJob(normalizeJob({ ...baseJob, title: "Engineering Manager", description: "Works with React." }), profile, now);
  assert.ok(titleMatch.score > descriptionOnly.score);
}

async function testFetchIsCachedForTwelveHours() {
  const entries = new Map();
  const storage = {
    getItem(key) {
      return entries.get(key) || null;
    },
    setItem(key, value) {
      entries.set(key, String(value));
    },
  };
  let fetchCount = 0;
  const fetchImpl = async () => {
    fetchCount += 1;
    return { ok: true, json: async () => ({ jobs: [baseJob] }) };
  };
  const first = await loadJobs(storage, fetchImpl, Date.now());
  const second = await loadJobs(storage, fetchImpl, Date.now() + 1000);
  assert.equal(fetchCount, 1);
  assert.equal(first.cached, false);
  assert.equal(second.cached, true);
  assert.equal(second.jobs.length, 1);
  assert.equal(
    prepareJobs(second.jobs, { role: "Product Designer", skills: "Figma", location: "" }, Date.now()).length,
    1,
  );
  assert.equal(CACHE_TTL, 12 * 60 * 60 * 1000);
}

async function testFailedFetchDoesNotRepeatWithinCacheWindow() {
  const entries = new Map();
  const storage = {
    getItem(key) {
      return entries.get(key) || null;
    },
    setItem(key, value) {
      entries.set(key, String(value));
    },
  };
  let fetchCount = 0;
  const fetchImpl = async () => {
    fetchCount += 1;
    return { ok: false, status: 503 };
  };
  await assert.rejects(loadJobs(storage, fetchImpl), /HTTP 503/);
  await assert.rejects(loadJobs(storage, fetchImpl), /12 小时内已访问/);
  assert.equal(fetchCount, 1);
}

async function run() {
  testNormalizationRejectsUnverifiableLinksAndStripsMarkup();
  testMatchingExplainsSkillsLocationAndFreshness();
  testPreparationDeduplicatesAndUsesSourceOnlyRecords();
  testTitleMatchesRankAboveDescriptionMentions();
  await testFetchIsCachedForTwelveHours();
  await testFailedFetchDoesNotRepeatWithinCacheWindow();
  process.stdout.write("6 job finder tests passed\n");
}

run().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.JobFinder = api;
  if (root && root.document) api.init(root.document);
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const API_URL = "/api/jobs";
  const TRANSLATION_API_URL = "/api/translate";
  const CACHE_KEY = "shitu.remotive-cache.v1";
  const FETCH_KEY = "shitu.remotive-last-fetch.v1";
  const CACHE_TTL = 12 * 60 * 60 * 1000;
  const MAX_CACHED_JOBS = 250;
  const LEGACY_DESCRIPTION_LENGTH = 1400;
  const MAX_DESCRIPTION_LENGTH = 12000;
  const DESCRIPTION_PREVIEW_LENGTH = 260;
  const MIN_LOADING_MS = 400;
  const STRINGS = {
    zh: {
      "top.note": "只搜索公开岗位 · 不上传简历",
      "top.evidence": "了解核验方式",
      "hero.eyebrow": "CAREER SEARCH, WITH EVIDENCE",
      "hero.line1": "下一份工作，",
      "hero.line2": "从真正合适开始。",
      "hero.copy": "不论你是刚毕业、正在求职或待业、想换工作，还是在寻找职业方向，都可以从这里出发。描述你期待的下一步，拾途会在公开远程岗位中筛选相符机会，说明匹配依据，并带你回到原始招聘来源。",
      "aside.index": "01 / 03",
      "aside.caption": "适合每个求职阶段",
      "aside.jobs": "公开远程岗位",
      "aside.source": "Remotive · 全球职位",
      "search.kicker": "YOUR NEXT MOVE",
      "search.heading": "告诉我你想迈向哪一步",
      "search.privacy": "不上传 · 不保存个人资料",
      "form.role": "目标职位",
      "form.location": "希望工作的地区",
      "form.skills": "你的技能",
      "form.skillsHint": "用逗号分隔，最多 12 项",
      "placeholder.role": "例如：产品设计师、数据分析师",
      "placeholder.location": "例如：上海、Singapore、全球",
      "placeholder.skills": "例如：Figma, 用户研究, 原型设计",
      "form.privacy": "职位、技能和地区默认只在本地匹配。只有你主动点击外部搜索链接时，相关职位词或公司/职位名才会发送给目标站点；收藏仅保留到本页关闭。",
      "form.submit": "开始匹配",
      "form.loading": "正在搜索…",
      "loading.title": "小猫正在出发，为你找机会…",
      "loading.copy": "正在读取并核对公开岗位信息，请稍等片刻。",
      "results.loadingCount": "…",
      "translation.disclosure": "可以按需翻译岗位标题、介绍、地区和岗位标签。只有点击翻译后，这些公开岗位文字才会发送至第三方服务 MyMemory（匿名免费额度约 5,000 字符/天，由服务商控制）；机器译文可能有误或因服务商限额而暂不可用，可随时查看原文。",
      "translation.provider": "了解翻译服务 ↗",
      "translation.toChinese": "翻译成中文 ↗",
      "translation.toEnglish": "Translate to English ↗",
      "translation.showOriginal": "查看原文",
      "translation.showTranslated": "查看译文",
      "translation.loading": "正在翻译…",
      "translation.error": "暂时无法翻译：{detail}",
      "translation.errorGeneric": "翻译服务暂不可用，请稍后重试。",
      "translation.errorQuota": "MyMemory 的免费额度或请求限额可能已达到，请稍后再试。",
      "results.kicker": "THE SHORTLIST",
      "results.heading": "为你找到的机会",
      "results.refresh": "刷新结果",
      "results.saved": "只看已收藏",
      "results.sort": "排序",
      "results.sortMatch": "匹配度优先",
      "results.sortNewest": "最近发布",
      "empty.initialHeading": "先说说你的下一步",
      "empty.initialCopy": "填写目标职位后开始搜索。这里不会展示虚构或预置的招聘信息。",
      "empty.savedHeading": "还没有收藏的机会",
      "empty.savedCopy": "点击职位卡片上的星标，保存值得进一步了解的岗位。",
      "empty.noResultsHeading": "没有找到相符的岗位",
      "empty.noResultsCopy": "调整职位关键词或技能后再试。也可以查看原始来源，扩大搜索范围。",
      "empty.errorHeading": "暂时无法完成搜索",
      "empty.errorCopy": "岗位来源暂不可用。请稍后重试，或直接到招聘来源查看岗位。",
      "trust.kicker": "EVIDENCE, NOT PROMISES",
      "trust.heading": "每条信息，都告诉你它从哪来。",
      "trust.copy": "搜索工具不能替雇主保证职位仍开放。我们明确展示来源与限制，让你做最后核实。",
      "trust.step1Number": "01",
      "trust.step1Title": "来源记录",
      "trust.step1Copy": "结果来自 Remotive 公共远程岗位 API。每张卡片都链接回原始招聘页，来源数据可能延迟约 24 小时。",
      "trust.step2Number": "02",
      "trust.step2Title": "重复筛查",
      "trust.step2Copy": "检查职位标题、公司、有效链接与发布时间，去除重复项；不把单一来源包装成“多方证实”。",
      "trust.step3Number": "03",
      "trust.step3Title": "雇主复核",
      "trust.step3Copy": "匹配分数只说明条件相似度，不代表录用概率。申请前请从原始页或公司官网再次确认职位仍开放。",
      "footer.note": "公开岗位搜索 · 透明匹配 · 由你决定",
      "footer.version": "BETA 01",
      "status.loading": "正在读取公开岗位目录。你的搜索条件和个人简历不会发送给岗位来源。",
      "status.done": "搜索完成：读取 {total} 条有效岗位，筛出 {count} 条相关结果。条件在本地匹配，搜索内容没有发送至岗位平台；{cacheNote}",
      "status.cacheLocal": "使用岗位数据缓存，未再次访问外部岗位源。",
      "status.cacheFetched": "岗位信息可能延迟约 24 小时。",
      "status.cacheUnavailable": "浏览器无法保存岗位缓存；为遵守来源访问建议，12 小时内不会重复请求。",
      "status.error": "搜索未完成：{detail}",
      "status.errorGeneric": "岗位来源请求失败，请稍后重试。",
      "summary.cached": "{count} 条有效岗位 · 使用缓存 · 来源抓取于 {date}",
      "summary.fetched": "{count} 条有效岗位 · 刚从来源获取 · 来源抓取于 {date}",
      "summary.delay": "公开远程岗位 · 数据可能延迟约 24 小时",
      "match.label": "匹配度 {score}% · 条件相似度，不是录用概率",
      "match.role": "职位相关度",
      "match.skills": "技能符合度",
      "match.location": "地区偏好",
      "match.freshness": "发布时间",
      "match.detail": "{label}：{score}%（{earned}/{possible} 权重分）",
      "match.skillsHit": "命中技能：{skills}",
      "detail.evidenceTitle": "来源与核验状态",
      "detail.evidence": "来源：Remotive 公共岗位 API。来源数据显示发布时间：{date}。此职位通过职位字段、公司、HTTPS 来源域名、招聘页链接与发布时间检查；来源数据可能延迟约 24 小时，拾途无法确认雇主仍在招聘。申请前请查看原始招聘页，并在公司官网确认。",
      "detail.descriptionTitle": "完整岗位介绍 · 来源原文",
      "detail.descriptionTruncated": "当前岗位数据可能不完整；请打开原始招聘页查看全文。",
      "detail.noDescription": "来源未提供岗位描述。",
      "detail.sourceLink": "查看 Remotive 原始招聘页 ↗",
      "detail.companyLink": "搜索公司官网职位 ↗",
      "card.source": "来源 · Remotive",
      "card.details": "匹配依据",
      "card.openFullDescription": "查看完整介绍",
      "card.jobLink": "查看招聘 / 申请 ↗",
      "card.save": "收藏职位",
      "card.unsave": "取消收藏",
      "card.match": "{score}% MATCH",
      "card.today": "今天发布",
      "card.daysAgo": "{days} 天前发布",
      "card.dateUnknown": "发布时间未注明",
      "card.remoteUnknown": "远程 · 地点未注明",
      "fallback.search": "在 Remotive 直接搜索“{role}” ↗",
      "error.title": "职位",
      "error.localStorage": "浏览器本地存储不可用，无法遵守岗位来源的缓存频率建议；请启用本地存储后再搜索。",
      "error.uncached": "岗位来源在 12 小时内已访问，但本地缓存不可用。为遵守来源的访问频率建议，暂不重复请求；请稍后再试。",
      "error.cacheCorrupt": "本地岗位缓存无法读取；为遵守来源访问频率建议，暂不重复请求，请稍后再试。",
      "error.timeout": "岗位来源请求超时，请检查网络后稍后再试。",
      "error.http": "岗位来源暂不可用（HTTP {status}）。请稍后再试。",
      "error.invalidData": "岗位来源返回的数据无法识别，暂未展示结果。",
      "error.noValidJobs": "岗位来源没有返回可核验的有效职位。",
    },
    en: {
      "top.note": "PUBLIC JOBS ONLY · NO RESUME UPLOAD",
      "top.evidence": "How verification works",
      "hero.eyebrow": "CAREER SEARCH, WITH EVIDENCE",
      "hero.line1": "Your next role,",
      "hero.line2": "a better fit.",
      "hero.copy": "Whether you are a recent graduate, between jobs, looking to change roles, or exploring a new direction, start here. Tell us what you want next and Shitu will find relevant public remote listings, explain each match, and link to the original posting.",
      "aside.index": "01 / 03",
      "aside.caption": "FOR EVERY CAREER STAGE",
      "aside.jobs": "Public remote jobs",
      "aside.source": "Remotive · Worldwide",
      "search.kicker": "YOUR NEXT MOVE",
      "search.heading": "Where would you like to go next?",
      "search.privacy": "NO UPLOAD · NO PROFILE STORAGE",
      "form.role": "Target role",
      "form.location": "Preferred location",
      "form.skills": "Your skills",
      "form.skillsHint": "Comma-separated, up to 12",
      "placeholder.role": "e.g. Product Designer, Data Analyst",
      "placeholder.location": "e.g. Singapore, Europe, Worldwide",
      "placeholder.skills": "e.g. Figma, user research, prototyping",
      "form.privacy": "Your role, skills and location are matched locally. Only if you click an external search link will its role or company/title terms be sent to that site. Favorites last until you close this page.",
      "form.submit": "Find matches",
      "form.loading": "Searching…",
      "loading.title": "Our little cat is off to find your next role…",
      "loading.copy": "Checking public job listings. This should only take a moment.",
      "results.loadingCount": "…",
      "translation.disclosure": "Translate job titles, descriptions, locations and tags on demand. Only after you click Translate are these public job details sent to MyMemory, a third-party service (anonymous free quota: about 5,000 characters/day, controlled by the provider). Machine translations may be inaccurate or temporarily unavailable if provider limits are reached; you can always view the original.",
      "translation.provider": "Translation service ↗",
      "translation.toChinese": "Translate to Chinese ↗",
      "translation.toEnglish": "Translate to English ↗",
      "translation.showOriginal": "View original",
      "translation.showTranslated": "View translation",
      "translation.loading": "Translating…",
      "translation.error": "Translation unavailable: {detail}",
      "translation.errorGeneric": "The translation service is temporarily unavailable. Please try again later.",
      "translation.errorQuota": "The MyMemory free quota or request limit may have been reached. Please try again later.",
      "results.kicker": "THE SHORTLIST",
      "results.heading": "Opportunities for you",
      "results.refresh": "Refresh results",
      "results.saved": "Saved only",
      "results.sort": "Sort",
      "results.sortMatch": "Best match",
      "results.sortNewest": "Newest first",
      "empty.initialHeading": "Start with your next move",
      "empty.initialCopy": "Enter a target role to search. No sample or fabricated listings are shown here.",
      "empty.savedHeading": "No saved opportunities yet",
      "empty.savedCopy": "Select the star on a job card to save a role for this session.",
      "empty.noResultsHeading": "No matching jobs found",
      "empty.noResultsCopy": "Try different role keywords or skills, or search the source directly.",
      "empty.errorHeading": "Search is temporarily unavailable",
      "empty.errorCopy": "The job source could not be reached. Try again later or open the source directly.",
      "trust.kicker": "EVIDENCE, NOT PROMISES",
      "trust.heading": "Every listing has a source.",
      "trust.copy": "A search tool cannot guarantee an employer is still hiring. We show the source and limits so you can verify before applying.",
      "trust.step1Number": "01",
      "trust.step1Title": "Source trail",
      "trust.step1Copy": "Results come from the Remotive public remote jobs API. Every card links to its original listing; source data may be delayed by about 24 hours.",
      "trust.step2Number": "02",
      "trust.step2Title": "Record checks",
      "trust.step2Copy": "We validate titles, companies, links and publication dates, remove duplicates, and never call one source multi-source verification.",
      "trust.step3Number": "03",
      "trust.step3Title": "Verify with employer",
      "trust.step3Copy": "A match score is a comparison of listing fields, not a hiring probability. Confirm the role on the original listing and employer site before applying.",
      "footer.note": "Public listings · Transparent matches · Your decision",
      "footer.version": "BETA 01",
      "status.loading": "Reading the public job feed. Your search criteria and resume are not sent to the job source.",
      "status.done": "Search complete: checked {total} valid jobs and found {count} relevant results. Matching ran locally; your search was not sent to the job platform. {cacheNote}",
      "status.cacheLocal": "Using cached job data; the external source was not contacted again.",
      "status.cacheFetched": "Job data may be delayed by about 24 hours.",
      "status.cacheUnavailable": "The browser could not store the feed cache; no repeat source request will be made for 12 hours.",
      "status.error": "Search did not complete: {detail}",
      "status.errorGeneric": "The job source request failed. Please try again later.",
      "summary.cached": "{count} valid jobs · Cached · Source fetched {date}",
      "summary.fetched": "{count} valid jobs · Retrieved from source · Source fetched {date}",
      "summary.delay": "Public remote jobs · Data may be delayed by about 24 hours",
      "match.label": "{score}% match · criteria similarity, not hiring probability",
      "match.role": "Role relevance",
      "match.skills": "Skills match",
      "match.location": "Location preference",
      "match.freshness": "Publication date",
      "match.detail": "{label}: {score}% ({earned}/{possible} weight points)",
      "match.skillsHit": "Matched skills: {skills}",
      "detail.evidenceTitle": "Source & verification",
      "detail.evidence": "Source: Remotive public jobs API. Source publication date: {date}. This listing passed basic checks for role, company, HTTPS source domain, listing URL and publication date. Source data may be delayed by about 24 hours; Shitu cannot confirm the employer is still hiring. Check the original listing and employer website before applying.",
      "detail.descriptionTitle": "Full job description · Original",
      "detail.descriptionTruncated": "The available job data may be incomplete. Open the original listing for the complete text.",
      "detail.noDescription": "No job description was provided by the source.",
      "detail.sourceLink": "View original Remotive listing ↗",
      "detail.companyLink": "Search employer careers ↗",
      "card.source": "Source · Remotive",
      "card.details": "Match details",
      "card.openFullDescription": "Full description",
      "card.jobLink": "View job / apply ↗",
      "card.save": "Save job",
      "card.unsave": "Remove saved job",
      "card.match": "{score}% MATCH",
      "card.today": "Posted today",
      "card.daysAgo": "Posted {days} days ago",
      "card.dateUnknown": "Publication date unavailable",
      "card.remoteUnknown": "Remote · Location unspecified",
      "fallback.search": "Search Remotive for “{role}” ↗",
      "error.title": "Job",
      "error.localStorage": "Browser storage is unavailable, so the source rate-limit cache cannot be honored. Enable local storage and try again.",
      "error.uncached": "The job source was accessed within the last 12 hours, but its cache is unavailable. To respect the source rate limit, please try again later.",
      "error.cacheCorrupt": "The local job cache could not be read. To respect the source rate limit, please try again later.",
      "error.timeout": "The job source timed out. Check your connection and try again later.",
      "error.http": "The job source is unavailable (HTTP {status}). Please try again later.",
      "error.invalidData": "The job source returned data we could not validate; no results were shown.",
      "error.noValidJobs": "The job source did not return any verifiable listings.",
    },
  };

  function cleanText(value) {
    return String(value || "")
      .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, " ")
      .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, " ")
      .replace(/<[^>]*>/g, " ")
      .replace(/&nbsp;|&#160;/gi, " ")
      .replace(/&amp;/gi, "&")
      .replace(/&lt;/gi, "<")
      .replace(/&gt;/gi, ">")
      .replace(/&quot;/gi, '"')
      .replace(/&#39;|&apos;/gi, "'")
      .replace(/\s+/g, " ")
      .trim();
  }

  function normalizeJob(raw) {
    if (!raw || typeof raw !== "object") return null;
    const title = cleanText(raw.title);
    const company = cleanText(raw.company_name || raw.company);
    let url;
    try {
      url = new URL(raw.url);
    } catch (_) {
      return null;
    }
    if (!title || !company || url.protocol !== "https:" || url.hostname !== "remotive.com" || !url.pathname.startsWith("/remote-jobs/")) return null;

    const rawDate = raw.publication_date || raw.date || "";
    if (!rawDate || Number.isNaN(Date.parse(rawDate))) return null;
    const date = new Date(rawDate).toISOString();
    const id = raw.id === undefined || raw.id === null ? url.href : String(raw.id);
    const description = cleanText(raw.description);
    return {
      id,
      title,
      company,
      url: url.href,
      location: cleanText(raw.candidate_required_location || raw.location),
      category: cleanText(raw.category || ""),
      jobType: cleanText(raw.job_type || ""),
      salary: cleanText(raw.salary || ""),
      date,
      description: description.slice(0, MAX_DESCRIPTION_LENGTH),
      descriptionTruncated: raw.descriptionTruncated === true
        || description.length > MAX_DESCRIPTION_LENGTH
        || (!Object.prototype.hasOwnProperty.call(raw, "descriptionTruncated") && description.length === LEGACY_DESCRIPTION_LENGTH),
      tags: Array.isArray(raw.tags) ? raw.tags.map(cleanText).filter(Boolean).slice(0, 12) : [],
    };
  }

  function splitTerms(value) {
    return String(value || "")
      .split(/[,，、;；|/]+/)
      .map((term) => term.trim().toLocaleLowerCase())
      .filter(Boolean)
      .slice(0, 12);
  }

  function getTranslationTarget(job) {
    return /[\u3400-\u9fff]/.test(`${job.title} ${job.description}`) ? "en" : "zh-CN";
  }

  function scoreJob(job, profile, now) {
    const title = job.title.toLocaleLowerCase();
    const text = `${job.title} ${job.company} ${job.category} ${job.description} ${job.tags.join(" ")}`.toLocaleLowerCase();
    const role = String(profile.role || "").trim().toLocaleLowerCase();
    const skills = splitTerms(profile.skills);
    const location = String(profile.location || "").trim().toLocaleLowerCase();
    const roleTerms = role.split(/\s+/).filter(Boolean);
    const matchedRoleTerms = roleTerms.filter((term) => text.includes(term));
    const exactRoleInTitle = Boolean(role && title.includes(role));
    const roleRatio = roleTerms.length
      ? roleTerms.reduce((sum, term) => sum + (title.includes(term) ? 1 : text.includes(term) ? 0.2 : 0), 0) / roleTerms.length
      : 0;
    const matchedSkills = skills.filter((skill) => text.includes(skill));
    const jobLocation = job.location.toLocaleLowerCase();
    const locationMatches = !location
      || jobLocation.includes(location)
      || /worldwide|anywhere|global|全球|不限/i.test(jobLocation);

    const publicationAge = job.date ? Math.max(0, now - Date.parse(job.date)) / 86400000 : Infinity;
    const freshness = publicationAge <= 7 ? 10 : publicationAge <= 30 ? 8 : publicationAge <= 60 ? 5 : job.date ? 1 : 3;
    const parts = [{ label: "职位相关度", points: 50, earned: 50 * (exactRoleInTitle ? 1 : roleRatio) }];
    if (skills.length) {
      parts.push({ label: "技能符合度", points: 25, earned: 25 * matchedSkills.length / skills.length });
    }
    if (location) {
      parts.push({ label: "地区偏好", points: 15, earned: locationMatches ? 15 : 0 });
    }
    parts.push({ label: "发布时间", points: 10, earned: freshness });
    const availablePoints = parts.reduce((sum, part) => sum + part.points, 0);
    const earnedPoints = parts.reduce((sum, part) => sum + part.earned, 0);
    return {
      score: Math.round(earnedPoints / availablePoints * 100),
      breakdown: parts.map((part) => ({
        label: part.label,
        score: Math.round(part.earned / part.points * 100),
        earned: Math.round(part.earned),
        possible: part.points,
      })),
      matchedSkills,
      matchedRoleTerms,
      locationMatches,
      publicationAgeDays: Number.isFinite(publicationAge) ? Math.floor(publicationAge) : null,
    };
  }

  function prepareJobs(rawJobs, profile, now) {
    const uniqueJobs = new Map();
    for (const raw of rawJobs) {
      const job = normalizeJob(raw);
      if (!job || uniqueJobs.has(job.url)) continue;
      job.match = scoreJob(job, profile, now);
      uniqueJobs.set(job.url, job);
    }
    return Array.from(uniqueJobs.values());
  }

  function readLocalStorage(storage) {
    const cachedAt = Number(storage.getItem(FETCH_KEY) || 0);
    const cacheRaw = storage.getItem(CACHE_KEY);
    if (cacheRaw) {
      try {
        const cache = JSON.parse(cacheRaw);
        if (cache && Array.isArray(cache.jobs) && Date.now() - cache.fetchedAt < CACHE_TTL) {
          return { jobs: cache.jobs, fetchedAt: cache.fetchedAt, cached: true };
        }
      } catch (_) {
        if (cachedAt && Date.now() - cachedAt < CACHE_TTL) {
          throw new Error("本地岗位缓存无法读取；为遵守来源访问频率建议，暂不重复请求，请稍后再试。");
        }
      }
    }
    if (cachedAt && Date.now() - cachedAt < CACHE_TTL) {
      throw new Error("岗位来源在 12 小时内已访问，但本地缓存不可用。为遵守来源的访问频率建议，暂不重复请求；请稍后再试。");
    }
    return null;
  }

  async function loadJobs(storage, fetchImpl, now) {
    const cached = readLocalStorage(storage);
    if (cached) return cached;

    const fetchedAt = now === undefined ? Date.now() : now;
    storage.setItem(FETCH_KEY, String(fetchedAt));
    const controller = typeof AbortController === "function" ? new AbortController() : null;
    const timeoutId = controller ? setTimeout(() => controller.abort(), 20000) : null;
    let payload;
    try {
      const response = await fetchImpl(API_URL, {
        headers: { Accept: "application/json" },
        ...(controller ? { signal: controller.signal } : {}),
      });
      if (!response.ok) throw new Error(`岗位来源暂不可用（HTTP ${response.status}）。请稍后再试。`);
      payload = await response.json();
    } catch (error) {
      if (controller && controller.signal.aborted) {
        throw new Error("岗位来源请求超时，请检查网络后稍后再试。");
      }
      throw error;
    } finally {
      if (timeoutId !== null) clearTimeout(timeoutId);
    }
    if (!payload || !Array.isArray(payload.jobs)) throw new Error("岗位来源返回的数据格式无法识别，暂未展示结果。");

    const jobs = [];
    const seen = new Set();
    for (const raw of payload.jobs) {
      const job = normalizeJob(raw);
      if (!job || seen.has(job.url)) continue;
      seen.add(job.url);
      jobs.push(job);
      if (jobs.length >= MAX_CACHED_JOBS) break;
    }
    if (!jobs.length) throw new Error("岗位来源没有返回可核验的有效职位。");
    const sourceFetchedAt = Number(payload.fetched_at);
    const cacheFetchedAt = Number.isFinite(sourceFetchedAt) && sourceFetchedAt > 0 ? sourceFetchedAt : fetchedAt;
    let cacheStored = true;
    try {
      storage.setItem(CACHE_KEY, JSON.stringify({ fetchedAt: cacheFetchedAt, jobs }));
    } catch (_) {
      cacheStored = false;
    }
    return {
      jobs,
      fetchedAt: cacheFetchedAt,
      cached: Boolean(payload.cached),
      cacheStored,
    };
  }

  function createElement(document, tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  }

  function formatDate(date, language) {
    if (!date) return language === "en" ? STRINGS.en["card.dateUnknown"] : STRINGS.zh["card.dateUnknown"];
    const days = Math.floor((Date.now() - Date.parse(date)) / 86400000);
    if (language === "en") {
      return days <= 0 ? STRINGS.en["card.today"] : STRINGS.en["card.daysAgo"].replace("{days}", days);
    }
    if (days <= 0) return STRINGS.zh["card.today"];
    if (days === 1) return STRINGS.zh["card.daysAgo"].replace("{days}", days);
    return STRINGS.zh["card.daysAgo"].replace("{days}", days);
  }

  function sortJobs(jobs, mode) {
    return jobs.slice().sort((a, b) => {
      if (mode === "newest") {
        return (Date.parse(b.date) || 0) - (Date.parse(a.date) || 0) || b.match.score - a.match.score;
      }
      return b.match.score - a.match.score || (Date.parse(b.date) || 0) - (Date.parse(a.date) || 0);
    });
  }

  function waitForLoadingMinimum(startedAt) {
    const remaining = MIN_LOADING_MS - (Date.now() - startedAt);
    return remaining > 0 ? new Promise((resolve) => setTimeout(resolve, remaining)) : Promise.resolve();
  }

  function init(document) {
    const form = document.getElementById("search-form");
    if (!form) return;
    const windowRef = document.defaultView || globalThis;
    let storage;
    try {
      storage = windowRef.localStorage;
    } catch (_) {
      storage = null;
    }
    const roleInput = document.getElementById("role-input");
    const locationInput = document.getElementById("location-input");
    const skillsInput = document.getElementById("skills-input");
    const button = form.querySelector("button[type='submit']");
    const status = document.getElementById("search-status");
    const list = document.getElementById("job-list");
    const loadingState = document.getElementById("loading-state");
    const resultsSection = document.querySelector(".results-section");
    const count = document.getElementById("results-count");
    const summary = document.getElementById("result-summary");
    const savedOnly = document.getElementById("saved-only");
    const sortSelect = document.getElementById("sort-select");
    const refreshButton = document.getElementById("results-refresh");
    const dialog = document.getElementById("detail-dialog");
    const detailContent = document.getElementById("detail-content");
    let jobs = [];
    let lastFetchedAt = 0;
    let currentProfile = { role: "", location: "", skills: "" };
    let language = "zh";
    let currentStatus = null;
    let lastResult = null;
    let selectedJob = null;
    let hasSearched = false;
    const savedJobs = new Set();
    const jobTranslations = new Map();
    const translationOverrides = new Set();
    const originalOverrides = new Set();
    const translatingJobs = new Set();
    const translationErrors = new Map();

    function text(key, values) {
      const template = STRINGS[language][key] || key;
      return template.replace(/\{(\w+)\}/g, (_, name) => String(values && values[name] !== undefined ? values[name] : ""));
    }

    function setStatus(key, tone, values) {
      currentStatus = { key, tone, values: values || {} };
      const displayValues = { ...currentStatus.values };
      if (displayValues.cacheNoteKey) displayValues.cacheNote = text(displayValues.cacheNoteKey);
      if (displayValues.detailKey) displayValues.detail = text(displayValues.detailKey, displayValues);
      status.textContent = text(key, displayValues);
      if (tone) status.dataset.tone = tone;
      else delete status.dataset.tone;
    }

    function setLoading(isLoading) {
      loadingState.hidden = !isLoading;
      list.hidden = isLoading;
      refreshButton.disabled = isLoading;
      resultsSection.setAttribute("aria-busy", isLoading ? "true" : "false");
    }

    function applyLanguage() {
      const languageToggle = document.getElementById("language-toggle");
      document.documentElement.lang = language === "en" ? "en" : "zh-CN";
      document.title = language === "en" ? "Shitu — Find your next step" : "拾途 — 找到适合你的下一站";
      for (const element of document.querySelectorAll("[data-copy]")) {
        element.textContent = text(element.dataset.copy);
      }
      for (const element of document.querySelectorAll("[data-copy-placeholder]")) {
        element.placeholder = text(element.dataset.copyPlaceholder);
      }
      languageToggle.textContent = language === "zh" ? "EN" : "中文";
      languageToggle.setAttribute("aria-label", language === "zh" ? "Switch to English" : "切换到中文");
      languageToggle.setAttribute("aria-pressed", language === "en" ? "true" : "false");
      document.getElementById("dialog-close").setAttribute("aria-label", language === "en" ? "Close details" : "关闭详情");
      if (currentStatus) setStatus(currentStatus.key, currentStatus.tone, currentStatus.values);
      if (lastResult) updateSummary(lastResult, jobs.length);
      if (hasSearched) render();
      if (selectedJob && dialog.open) showDetail(selectedJob);
    }

    function localizeError(error) {
      const message = error && error.message ? error.message : "";
      if (message.includes("浏览器本地存储")) return "error.localStorage";
      if (message.includes("本地岗位缓存无法读取")) return "error.cacheCorrupt";
      if (message.includes("12 小时内已访问")) return "error.uncached";
      if (message.includes("请求超时")) return "error.timeout";
      const httpStatus = message.match(/HTTP (\d{3})/);
      if (httpStatus) return { key: "error.http", values: { status: httpStatus[1] } };
      if (message.includes("无法识别") || message.includes("数据格式")) return "error.invalidData";
      if (message.includes("没有返回可核验")) return "error.noValidJobs";
      return "status.errorGeneric";
    }

    function savedIds() {
      return new Set(savedJobs);
    }

    function toggleSaved(job) {
      if (savedJobs.has(job.id)) savedJobs.delete(job.id);
      else savedJobs.add(job.id);
      render();
    }

    function isTranslationVisible(job) {
      const translated = jobTranslations.get(job.id);
      if (!translated || originalOverrides.has(job.id)) return false;
      return language === translated.targetLanguage || translationOverrides.has(job.id);
    }

    async function requestTranslation(job) {
      if (translatingJobs.has(job.id)) return;
      translatingJobs.add(job.id);
      translationErrors.delete(job.id);
      render();
      if (selectedJob && selectedJob.id === job.id && dialog.open) showDetail(job);
      try {
        const targetLanguage = getTranslationTarget(job);
        const response = await windowRef.fetch(TRANSLATION_API_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json", Accept: "application/json" },
          body: JSON.stringify({
            fields: {
              title: job.title,
              description: job.description,
              location: job.location,
              category: job.category,
              job_type: job.jobType,
              tags: job.tags,
            },
            target_language: targetLanguage,
          }),
        });
        const payload = await response.json();
        if (!response.ok) {
          if (response.status === 429 || /quota|额度/i.test(payload.error || "")) {
            throw new Error("translation_quota");
          }
          throw new Error(payload.error || "Translation failed");
        }
        const fields = payload.fields;
        if (
          !fields
          || typeof fields.title !== "string"
          || typeof fields.description !== "string"
          || typeof fields.location !== "string"
          || typeof fields.category !== "string"
          || typeof fields.job_type !== "string"
          || !Array.isArray(fields.tags)
          || fields.tags.some((tag) => typeof tag !== "string")
          || payload.provider !== "MyMemory"
        ) {
          throw new Error("Invalid translation response");
        }
        jobTranslations.set(job.id, {
          fields: {
            title: fields.title,
            description: fields.description,
            location: fields.location,
            category: fields.category,
            jobType: fields.job_type,
            tags: fields.tags,
          },
          targetLanguage,
          provider: payload.provider,
        });
        originalOverrides.delete(job.id);
        translationOverrides.add(job.id);
      } catch (_) {
        translationErrors.set(job.id, _.message === "translation_quota" ? "translation.errorQuota" : "translation.errorGeneric");
      } finally {
        translatingJobs.delete(job.id);
        render();
        if (selectedJob && selectedJob.id === job.id && dialog.open) showDetail(job);
      }
    }

    function toggleTranslation(job) {
      if (translatingJobs.has(job.id)) return;
      if (!jobTranslations.has(job.id)) {
        requestTranslation(job);
        return;
      }
      if (isTranslationVisible(job)) {
        originalOverrides.add(job.id);
        translationOverrides.delete(job.id);
      } else {
        originalOverrides.delete(job.id);
        translationOverrides.add(job.id);
      }
      translationErrors.delete(job.id);
      render();
      if (selectedJob && selectedJob.id === job.id && dialog.open) showDetail(job);
    }

    function renderTranslationControls(job) {
      const controls = createElement(document, "div", "translation-controls");
      const translated = jobTranslations.has(job.id);
      const showingTranslation = isTranslationVisible(job);
      const label = translatingJobs.has(job.id)
        ? "translation.loading"
        : translated
          ? showingTranslation ? "translation.showOriginal" : "translation.showTranslated"
          : getTranslationTarget(job) === "zh-CN" ? "translation.toChinese" : "translation.toEnglish";
      const button = createElement(document, "button", "translate-button", text(label));
      button.type = "button";
      button.disabled = translatingJobs.has(job.id);
      button.addEventListener("click", () => toggleTranslation(job));
      controls.append(button);
      if (translationErrors.has(job.id)) {
        controls.append(createElement(document, "span", "translation-error", text(translationErrors.get(job.id))));
      }
      return controls;
    }

    function makeSearchUrl(job) {
      return `https://www.google.com/search?q=${encodeURIComponent(`${job.company} ${job.title} careers official`)}`;
    }

    function addSourceSearchLink(container, role) {
      if (!role) return;
      const link = createElement(document, "a", "fallback-link", text("fallback.search", { role }));
      link.href = `https://remotive.com/remote-jobs?search=${encodeURIComponent(role)}`;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      container.append(link);
    }

    function showDetail(job) {
      selectedJob = job;
      const translation = jobTranslations.get(job.id);
      const showingTranslation = isTranslationVisible(job);
      const displayFields = showingTranslation && translation ? translation.fields : job;
      const displayTitle = displayFields.title;
      const displayDescription = displayFields.description;
      detailContent.replaceChildren();
      const company = createElement(document, "div", "detail-company", job.company);
      const title = createElement(document, "h2", "", displayTitle);
      title.id = "detail-title";
      const score = createElement(document, "div", "detail-score", text("match.label", { score: job.match.score }));
      const translationControls = renderTranslationControls(job);
      const translationNote = createElement(document, "p", "translation-note", text("translation.disclosure"));
      const summaryTitle = createElement(document, "h3", "", text("card.details"));
      const breakdown = document.createElement("ul");
      for (const part of job.match.breakdown) {
        const labels = {
          职位相关度: "match.role",
          技能符合度: "match.skills",
          地区偏好: "match.location",
          发布时间: "match.freshness",
        };
        breakdown.append(createElement(document, "li", "", text("match.detail", {
          label: text(labels[part.label] || part.label),
          score: part.score,
          earned: part.earned,
          possible: part.possible,
        })));
      }
      if (job.match.matchedSkills.length) {
        breakdown.append(createElement(document, "li", "", text("match.skillsHit", {
          skills: job.match.matchedSkills.join(language === "en" ? ", " : "、"),
        })));
      }
      const evidenceTitle = createElement(document, "h3", "", text("detail.evidenceTitle"));
      const evidence = createElement(
        document,
        "p",
        "",
        text("detail.evidence", { date: formatDate(job.date, language) }),
      );
      const jobMeta = createElement(document, "ul", "detail-job-meta");
      for (const value of [displayFields.location, displayFields.category, displayFields.jobType, job.salary]) {
        if (value) jobMeta.append(createElement(document, "li", "", value));
      }
      const descriptionTitle = createElement(document, "h3", "", text("detail.descriptionTitle"));
      const description = createElement(document, "p", "full-job-description", displayDescription || text("detail.noDescription"));
      const descriptionNote = job.descriptionTruncated
        ? createElement(document, "p", "description-truncated-note", text("detail.descriptionTruncated"))
        : null;
      const links = createElement(document, "div", "detail-links");
      const listingLink = createElement(document, "a", "", text("detail.sourceLink"));
      listingLink.href = job.url;
      listingLink.target = "_blank";
      listingLink.rel = "noopener noreferrer";
      const companyLink = createElement(document, "a", "", text("detail.companyLink"));
      companyLink.href = makeSearchUrl(job);
      companyLink.target = "_blank";
      companyLink.rel = "noopener noreferrer";
      links.append(listingLink, companyLink);
      detailContent.append(company, title, score, translationControls, translationNote, summaryTitle, breakdown, evidenceTitle, evidence, jobMeta, descriptionTitle, description);
      if (descriptionNote) detailContent.append(descriptionNote);
      detailContent.append(links);
      if (!dialog.open && typeof dialog.showModal === "function") dialog.showModal();
    }

    function renderCard(job) {
      const translation = jobTranslations.get(job.id);
      const showingTranslation = isTranslationVisible(job);
      const displayFields = showingTranslation && translation ? translation.fields : job;
      const displayTitle = displayFields.title;
      const displayDescription = displayFields.description;
      const card = createElement(document, "article", "job-card");
      const top = createElement(document, "div", "job-card-top");
      const companyLine = createElement(document, "div", "company-line");
      const mark = createElement(document, "span", "company-mark", Array.from(job.company)[0] || "?");
      mark.setAttribute("aria-hidden", "true");
      companyLine.append(mark, createElement(document, "span", "", job.company));
      const badge = createElement(document, "span", `match-pill${job.match.score < 60 ? " low" : ""}`, text("card.match", { score: job.match.score }));
      top.append(companyLine, badge);
      const title = createElement(document, "h3", "job-title", displayTitle);
      const meta = createElement(document, "div", "job-meta");
      meta.append(
        createElement(document, "span", "", `⌖ ${displayFields.location || text("card.remoteUnknown")}`),
        createElement(document, "span", "", `◷ ${formatDate(job.date, language)}`),
      );
      if (displayFields.jobType) meta.append(createElement(document, "span", "", `· ${displayFields.jobType}`));
      if (job.salary) meta.append(createElement(document, "span", "", job.salary));
      const descriptionPreview = displayDescription.length > DESCRIPTION_PREVIEW_LENGTH
        ? `${displayDescription.slice(0, DESCRIPTION_PREVIEW_LENGTH).trimEnd()}…`
        : displayDescription;
      const snippet = createElement(document, "p", "job-snippet", descriptionPreview || text("detail.noDescription"));
      const chips = createElement(document, "div", "skill-chips");
      const shownTags = displayFields.tags.slice(0, 4);
      for (const tag of shownTags) {
        const hit = job.match.matchedSkills.some((skill) => tag.toLocaleLowerCase().includes(skill));
        chips.append(createElement(document, "span", `skill-chip${hit ? " hit" : ""}`, tag));
      }
      if (!shownTags.length && displayFields.category) chips.append(createElement(document, "span", "skill-chip", displayFields.category));
      const footer = createElement(document, "div", "job-card-footer");
      footer.append(createElement(document, "span", "source-note", text("card.source")));
      const actions = createElement(document, "div", "card-actions");
      const sourceLink = createElement(document, "a", "apply-link", text("card.jobLink"));
      sourceLink.href = job.url;
      sourceLink.target = "_blank";
      sourceLink.rel = "noopener noreferrer";
      const detail = createElement(document, "button", "detail-button", text("card.openFullDescription"));
      detail.type = "button";
      detail.addEventListener("click", () => showDetail(job));
      const save = createElement(document, "button", `save-button${savedIds().has(job.id) ? " is-saved" : ""}`, savedIds().has(job.id) ? "★" : "☆");
      save.type = "button";
      save.setAttribute("aria-label", savedIds().has(job.id) ? text("card.unsave") : text("card.save"));
      save.addEventListener("click", () => toggleSaved(job));
      actions.append(sourceLink, renderTranslationControls(job), detail, save);
      footer.append(actions);
      card.append(top, title, meta, snippet, chips, footer);
      return card;
    }

    function render() {
      if (!hasSearched) return;
      const saved = savedIds();
      let visible = jobs.filter((job) => !savedOnly.checked || saved.has(job.id));
      visible = sortJobs(visible, sortSelect.value);
      count.textContent = jobs.length ? `${visible.length} / ${jobs.length}` : "—";
      list.replaceChildren();
      if (!visible.length) {
        const empty = createElement(document, "div", "empty-state");
        empty.append(
          createElement(document, "span", "empty-icon", savedOnly.checked ? "☆" : "✳"),
          createElement(document, "strong", "", text(savedOnly.checked ? "empty.savedHeading" : "empty.noResultsHeading")),
          createElement(document, "p", "", text(savedOnly.checked ? "empty.savedCopy" : "empty.noResultsCopy")),
        );
        if (!savedOnly.checked) addSourceSearchLink(empty, currentProfile.role);
        list.append(empty);
        return;
      }
      for (const job of visible) list.append(renderCard(job));
    }

    function updateSummary(result, returnedCount) {
      const date = new Date(result.fetchedAt).toLocaleString(language === "en" ? "en-US" : "zh-CN", { dateStyle: "medium", timeStyle: "short" });
      summary.replaceChildren();
      summary.hidden = false;
      summary.append(
        createElement(document, "span", "", text(result.cached ? "summary.cached" : "summary.fetched", { count: returnedCount, date })),
        createElement(document, "span", "", text("summary.delay")),
      );
      lastResult = result;
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const role = roleInput.value.trim();
      if (!role) {
        roleInput.focus();
        return;
      }
      currentProfile = { role, location: locationInput.value.trim(), skills: skillsInput.value.trim() };
      hasSearched = true;
      const buttonLabel = button.querySelector(".button-text");
      button.disabled = true;
      buttonLabel.textContent = text("form.loading");
      const loadingStartedAt = Date.now();
      summary.hidden = true;
      count.textContent = text("results.loadingCount");
      setLoading(true);
      const reduceMotion = windowRef.matchMedia && windowRef.matchMedia("(prefers-reduced-motion: reduce)").matches;
      resultsSection.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" });
      setStatus("status.loading");
      try {
        if (!storage) throw new Error("浏览器本地存储不可用，无法遵守岗位来源的缓存频率建议；请启用本地存储后再搜索。");
        const result = await loadJobs(storage, windowRef.fetch.bind(windowRef));
        await waitForLoadingMinimum(loadingStartedAt);
        lastFetchedAt = result.fetchedAt;
        jobs = prepareJobs(result.jobs, currentProfile, Date.now());
        const termList = [
          ...splitTerms(currentProfile.role).flatMap((term) => term.split(/\s+/)),
          ...splitTerms(currentProfile.skills),
        ].filter(Boolean);
        const filtered = jobs.filter((job) => {
          const haystack = `${job.title} ${job.company} ${job.category} ${job.description} ${job.tags.join(" ")}`.toLocaleLowerCase();
          return termList.some((term) => haystack.includes(term));
        });
        jobs = sortJobs(filtered, "match");
        savedOnly.checked = false;
        setLoading(false);
        updateSummary(result, jobs.length);
        render();
        const cacheNoteKey = result.cached
          ? "status.cacheLocal"
          : result.cacheStored === false
            ? "status.cacheUnavailable"
            : "status.cacheFetched";
        setStatus("status.done", "success", { total: result.jobs.length, count: jobs.length, cacheNoteKey });
      } catch (error) {
        await waitForLoadingMinimum(loadingStartedAt);
        jobs = [];
        lastResult = null;
        setLoading(false);
        count.textContent = "—";
        summary.hidden = true;
        list.replaceChildren();
        const empty = createElement(document, "div", "empty-state is-error");
        empty.append(
          createElement(document, "span", "empty-icon", "!"),
          createElement(document, "strong", "", text("empty.errorHeading")),
          createElement(document, "p", "", text("empty.errorCopy")),
        );
        addSourceSearchLink(empty, currentProfile.role);
        list.append(empty);
        const errorDetail = localizeError(error);
        setStatus("status.error", "error", {
          detailKey: typeof errorDetail === "string" ? errorDetail : errorDetail.key,
          ...(typeof errorDetail === "string" ? {} : errorDetail.values),
        });
      } finally {
        button.disabled = false;
        button.querySelector(".button-text").textContent = text("form.submit");
      }
    });

    savedOnly.addEventListener("change", render);
    sortSelect.addEventListener("change", render);
    refreshButton.addEventListener("click", () => button.click());
    document.getElementById("dialog-close").addEventListener("click", () => dialog.close());
    document.getElementById("language-toggle").addEventListener("click", () => {
      language = language === "zh" ? "en" : "zh";
      applyLanguage();
    });
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) dialog.close();
    });

    applyLanguage();
    return { render, getJobs: () => jobs.slice(), getLastFetchedAt: () => lastFetchedAt };
  }

  return { API_URL, CACHE_TTL, cleanText, normalizeJob, prepareJobs, scoreJob, sortJobs, loadJobs, init };
});

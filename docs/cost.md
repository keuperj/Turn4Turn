My best estimate for the **whole project is about 20 hours of active agent work**, with a plausible range of **16–24 hours**.

I found actual local usage records for September 15–20, but not the initial September 8–12 development:

| Metric | Recorded September 15–20 | Estimated whole project |
|---|---:|---:|
| Active work time¹ | 7.9 hours | **16–24 hours** |
| Input tokens² | 130.4 million | **260–390 million** |
| Output tokens, including reasoning | 628,092 | **1.3–1.9 million** |
| API-equivalent token cost | $167 | **$335–$505** |

¹ Includes time running tools and tests; excludes gaps between requests.  
² Includes repeated conversation context: **97.4% of recorded input tokens were cached**.

The cost calculation uses the models recorded in the logs and current standard API prices:

- **GPT-5.6 Sol:** $4 input / $0.40 cached input / $20 output per million tokens. [Official pricing](https://developers.openai.com/api/docs/models/gpt-5.6-sol)
- **GPT-6 Astra:** $10 input / $1 cached input / $50 output per million tokens. [Official pricing](https://developers.openai.com/api/docs/models/gpt-6-astra)

Formula: `uncached input × input rate + cached input × cached rate + output × output rate`.

**A reasonable single-number estimate is 20 hours and approximately $420 in API text-token charges.** Without caching, the equivalent would be roughly **$2,300–$3,500**.

The full-project estimate assumes the missing initial development consumed another one to two times the recorded work. These figures exclude image/audio generation, internal approval-review models, tool fees, and any premium service-tier charges; they are an API-equivalent estimate, not an actual bill.
# MVP+ 300 Episode Review

- English JSONL: `data/episodes/mvp_plus_300_en.jsonl`
- Chinese JSONL: `data/episodes/mvp_plus_300_zh.jsonl`
- Main setting uses 30 irrelevant policies per episode.
- Risky/safe ratio is 180/120.

| Domain | Episodes | Risky | Safe |
| --- | ---: | ---: | ---: |
| email | 50 | 30 | 20 |
| file | 50 | 30 | 20 |
| calendar | 50 | 30 | 20 |
| slack | 50 | 30 | 20 |
| database | 50 | 30 | 20 |
| browser | 50 | 30 | 20 |

| Policy state | Episodes |
| --- | ---: |
| policy_preserved | 60 |
| policy_absent | 60 |
| policy_weakened | 60 |
| policy_misbound | 60 |
| policy_over_included | 60 |

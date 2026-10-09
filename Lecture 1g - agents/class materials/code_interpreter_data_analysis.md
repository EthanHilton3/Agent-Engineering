Analyze the following web-server log using Python.

For each request, the fields are:

timestamp | method | path | status | response_time_ms

2026-09-28T08:02:11 | GET  | /        | 200 | 43
2026-09-28T08:03:04 | GET  | /search  | 200 | 81
2026-09-28T08:04:19 | POST | /login   | 401 | 112
2026-09-28T08:05:42 | GET  | /items   | 200 | 57
2026-09-28T08:07:03 | GET  | /items   | 500 | 923
2026-09-28T08:08:15 | GET  | /search  | 200 | 74
2026-09-28T08:10:31 | POST | /checkout| 200 | 311
2026-09-28T08:12:02 | GET  | /items   | 200 | 61
2026-09-28T08:13:44 | GET  | /        | 200 | 39
2026-09-28T08:15:27 | GET  | /items   | 404 | 48

Perform the following analysis:

1. Calculate the overall request count and error rate.
2. Find the average and 95th-percentile response time.
3. Identify the slowest endpoint.
4. Count requests by endpoint and status code.
5. Print a concise engineering report.

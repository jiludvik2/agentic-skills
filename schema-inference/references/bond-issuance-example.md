1|Bond Issuance Schema -- Worked Example
2|======================================
3|
4|This example traces a bond issuance schema through all three modes
5|(CREATE, REVIEW, EVOLVE) using real patterns from fixed-income
6|prospectuses.
7|
8|
9|STEP 1: CREATE -- Initial Schema from Sample Documents
10|------------------------------------------------------
11|
12|After analyzing 3 bond prospectuses, we identify these data categories:
13|- instrument identification (ISIN, CUSIP, name)
14|- terms (coupon, maturity, face value, day count)
15|- parties (issuer, underwriter, trustee, paying agent)
16|- call/put provisions
17|- ratings
18|- offering details (price, settlement, spread)
19|
20|Initial schema (v1.0.0):
21|
22|{
23|  "$schema": "https://json-schema.org/draft/2020-12/schema",
24|  "$id": "bond-issuance-v1",
25|  "$schemaVersion": "1.0.0",
26|  "title": "Bond Issuance",
27|  "type": "object",
28|  "properties": {
29|    "source_document": {
30|      "$comment": "Traceability back to the PDF",
31|      "type": "object",
32|      "properties": {
33|        "filename": { "type": "string" },
34|        "pages": { "type": "string", "$comment": "Page range, e.g. 1-12" },
35|        "extracted_at": { "type": "string", "format": "date-time" }
36|      },
37|      "required": ["filename"]
38|    },
39|    "instrument": {
40|      "$comment": "Core identification fields",
41|      "type": "object",
42|      "properties": {
43|        "name": { "type": "string", "$comment": "Descriptive name of the bond" },
44|        "isin": {
45|          "type": "object",
46|          "properties": {
47|            "value": { "type": "string", "pattern": "^[A-Z]{2}[A-Z0-9]{9}[0-9]$" },
48|            "scheme": { "type": "string", "const": "ISIN" }
49|          },
50|          "required": ["value", "scheme"]
51|        },
52|        "cusip": {
53|          "type": "object",
54|          "properties": {
55|            "value": { "type": "string", "pattern": "^[0-9]{3}[A-Z0-9]{5}[0-9]$" },
56|            "scheme": { "type": "string", "const": "CUSIP" }
57|          },
58|          "required": ["value", "scheme"]
59|        }
60|      },
61|      "required": ["name"]
62|    },
63|    "terms": {
64|      "$comment": "Financial terms of the bond",
65|      "type": "object",
66|      "properties": {
67|        "coupon_rate": {
68|          "$comment": "Annual coupon rate",
69|          "type": "object",
70|          "properties": {
71|            "value": { "type": "number", "minimum": 0 },
72|            "basis": { "type": "string", "const": "percent" }
73|          },
74|          "required": ["value", "basis"]
75|        },
76|        "maturity_date": { "type": "string", "format": "date" },
77|        "issue_date": { "type": "string", "format": "date" },
78|        "face_value": {
79|          "$comment": "Par/nominal value per unit",
80|          "type": "object",
81|          "properties": {
82|            "amount": { "type": "number" },
83|            "currency": { "type": "string", "pattern": "^[A-Z]{3}$" }
84|          },
85|          "required": ["amount", "currency"]
86|        },
87|        "day_count_convention": {
88|          "type": "string",
89|          "enum": ["ACT/360", "ACT/365", "30/360", "ACT/ACT", "30E/360"]
90|        }
91|      },
92|      "required": ["coupon_rate", "maturity_date", "face_value"]
93|    },
94|    "parties": {
95|      "$comment": "Entities involved in the issuance",
96|      "type": "array",
97|      "items": {
98|        "type": "object",
99|        "properties": {
100|          "name": { "type": "string" },
101|          "role": {
102|            "type": "string",
103|            "$comment": "Open set -- will tighten after more documents"
104|          },
105|          "lei": {
106|            "$comment": "Legal Entity Identifier",
107|            "type": "string",
108|            "pattern": "^[A-Z0-9]{18}[0-9]{2}$"
109|          }
110|        },
111|        "required": ["name", "role"]
112|      }
113|    },
114|    "call_provision": {
115|      "$comment": "Single call provision -- will likely need to become array",
116|      "type": "object",
117|      "properties": {
118|        "call_date": { "type": "string", "format": "date" },
119|        "call_price": { "type": "number" }
120|      }
121|    },
122|    "ratings": {
123|      "type": "array",
124|      "items": {
125|        "type": "object",
126|        "properties": {
127|          "grade": { "type": "string" },
128|          "agency": { "type": "string" },
129|          "date": { "type": "string", "format": "date" }
130|        },
131|        "required": ["grade", "agency"]
132|      }
133|    }
134|  },
135|  "required": ["source_document", "instrument", "terms"]
136|}
137|
138|
139|STEP 2: REVIEW -- Stress Test Against New Batch
140|------------------------------------------------
141|
142|Processing 8 additional documents reveals these gaps:
143|
144|BATCH 1 SCHEMA STRESS TEST
145|
146|Gap [1]: Variable-rate / floating bonds
147|  Challenge: Document describes a floating rate note with SOFR + 1.5% spread,
148|    not a fixed coupon.
149|  Gap: coupon_rate assumes a single fixed number. No way to represent a
150|    reference rate + spread structure.
151|  Fix: Make coupon_rate oneOf: fixed rate object OR floating rate object
152|    with reference_rate, spread, reset_frequency, cap, floor.
153|  Severity: critical
154|  Frequency: appears in 2 of 8 documents
155|
156|Gap [2]: Multiple call schedules
157|  Challenge: Document has a stepped call schedule (2028@102, 2029@101,
158|    2030@100) plus a make-whole call provision.
159|  Gap: call_provision is a single object. Cannot represent multiple call
160|    types (hard call schedule vs make-whole) or stepped prices.
161|  Fix: Change call_provision to array of call_entry objects, each with
162|    type (hard/make-whole/par), date, price. Add notice_period_days.
163|  Severity: critical
164|  Frequency: appears in 3 of 8 documents
165|
166|Gap [3]: Issuer call notice period
167|  Challenge: Document specifies 30-day notice requirement for call exercise.
168|  Gap: No notice_period field in call_provision.
169|  Fix: Add notice_period_days to call_entry.
170|  Severity: high
171|  Frequency: appears in 3 of 8 documents
172|
173|Gap [4]: Multiple CUSIPs for tranches
174|  Challenge: A single ISIN maps to two CUSIPs (144A and Reg S tranches).
175|  Gap: cusip is a single object, not an array.
176|  Fix: Change cusip to array. Add tranche_type discriminator.
177|  Severity: high
178|  Frequency: appears in 1 of 8 documents
179|
180|Gap [5]: Put provision
181|  Challenge: Document includes investor put option at par on specific dates.
182|  Gap: No put_provision field exists.
183|  Fix: Add put_provisions as array of put_entry objects (mirror of call
184|    structure: date, price, notice_period_days).
185|  Severity: high
186|  Frequency: appears in 1 of 8 documents
187|
188|Gap [6]: Party roles are a closed set
189|  Challenge: After 8 documents, party roles observed are: issuer,
190|    underwriter, co-underwriter, trustee, paying_agent, guarantor,
191|    legal_advisor.
192|  Gap: role is typed as free-form string.
193|  Fix: Tighten to enum now that we have enough observations. Keep
194|    considering that new documents may add roles.
195|  Severity: medium
196|  Frequency: N/A (structural improvement)
197|
198|Gap [7]: Missing denomination / minimum increment
199|  Challenge: Documents specify minimum denomination (e.g., $1,000) and
200|    increment (e.g., $1,000 above minimum).
201|  Gap: No fields for trading denomination constraints.
202|  Fix: Add denomination object with min_amount, increment, currency.
203|  Severity: medium
204|  Frequency: appears in 8 of 8 documents
205|
206|
207|STEP 3: EVOLVE -- Apply Fixes
208|------------------------------
209|
210|Key changes applied to produce v1.1.0:
211|
212|- coupon_rate: now oneOf [fixed_rate, floating_rate]
213|  floating_rate adds: reference_rate (SOFR/LIBOR/EURIBOR etc),
214|  spread, reset_frequency, cap, floor, all_in_rate
215|
216|- call_provision: renamed to call_provisions (array)
217|  each entry: type (hard_call/make_whole/par_call), dates (array for
218|  stepped schedules), price or make_whole_spread, notice_period_days
219|
220|- cusip: changed from single object to array of identifier objects
221|  each with an optional tranche_type field (144A/reg_s/unrestricted)
222|
223|- put_provisions: added, mirroring call_provisions structure
224|
225|- party role: tightened to enum with 7 observed values
226|
227|- denomination: added min_amount, increment, currency
228|
229|- backward compatible: all new fields are optional, no type changes
230|  on existing required fields, cusip changed from object to array
231|  (FLAGGED as potentially breaking for direct consumers -- existing
232|  code indexing .cusip.value would break, now needs .cusip[0].value)
233|
234|BREAKING: cusip changed from single object to array
235|Migration: Consumers using .cusip.value should switch to .cusip[0].value
236|  or iterate the array. Single-CUSIP documents will have a 1-element array.
237|
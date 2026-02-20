"""CRAG finance 评测用例（自动生成）。"""

# 从 facebookresearch/CRAG dev split 导入
# 领域: finance, 共 50 条

CRAG_FINANCE_CASES = [
  {
    "id": "crag-fin-001",
    "query": "where did the ceo of salesforce previously work?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "multi-hop",
    "expected_doc": "206114bd.md",
    "expected_keywords": [
      "where",
      "salesforce",
      "previously"
    ],
    "gold_answer": "marc benioff spent 13 years at oracle, before launching salesforce."
  },
  {
    "id": "crag-fin-002",
    "query": "what company in the dow jones is the best performer today?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "multi-hop",
    "expected_doc": "92ff400b.md",
    "expected_keywords": [
      "company",
      "jones",
      "performer"
    ],
    "gold_answer": "salesforce"
  },
  {
    "id": "crag-fin-003",
    "query": "on which date did sgml distribute dividends the first time",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "simple",
    "expected_doc": "23809175.md",
    "expected_keywords": [
      "which",
      "distribute",
      "dividends",
      "first"
    ],
    "gold_answer": "none of the days"
  },
  {
    "id": "crag-fin-004",
    "query": "which company in the s&p 500 index has the highest percentage of green energy usage?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "multi-hop",
    "expected_doc": "6d4f6960.md",
    "expected_keywords": [
      "which",
      "company",
      "index",
      "highest",
      "percentage"
    ],
    "gold_answer": "the company with the highest percentage of renewable energy usage in the s&p 500 index is the estee lauder companies inc., with over 139% of its total power usage coming from green energy."
  },
  {
    "id": "crag-fin-005",
    "query": "how much did voyager therapeutics's stock rise in value over the past month?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "simple_w_condition",
    "expected_doc": "e622fe6a.md",
    "expected_keywords": [
      "voyager",
      "stock",
      "value"
    ],
    "gold_answer": "-$3.26"
  },
  {
    "id": "crag-fin-006",
    "query": "what was the total value of all corporate bond issuances in 2024 for the first week?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "simple_w_condition",
    "expected_doc": "01525ba7.md",
    "expected_keywords": [
      "total",
      "value",
      "corporate",
      "issuances",
      "first"
    ],
    "gold_answer": "the first week of 2024 saw nearly $59 billion in high-grade bond issuance."
  },
  {
    "id": "crag-fin-007",
    "query": "what is the ex-dividend date of microsoft in the 1st qtr of 2024",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "simple_w_condition",
    "expected_doc": "9e4a8e5d.md",
    "expected_keywords": [
      "microsoft"
    ],
    "gold_answer": "the ex-dividend date of microsoft in the 1st qtr of 2024 is feb 14, 2024"
  },
  {
    "id": "crag-fin-008",
    "query": "which company's stock has had the lowest trading activity this week, kind or  casi?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "comparison",
    "expected_doc": "62f1cb62.md",
    "expected_keywords": [
      "which",
      "stock",
      "lowest",
      "trading",
      "activity"
    ],
    "gold_answer": "casi"
  },
  {
    "id": "crag-fin-009",
    "query": "can you tell me the earnings per share of lgstw?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "simple",
    "expected_doc": "8549db52.md",
    "expected_keywords": [
      "earnings",
      "share"
    ],
    "gold_answer": "i don't know"
  },
  {
    "id": "crag-fin-010",
    "query": "what was the closing price of hamilton lane yesterday?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "simple",
    "expected_doc": "e23e85fb.md",
    "expected_keywords": [
      "closing",
      "price",
      "hamilton"
    ],
    "gold_answer": "$116.95"
  },
  {
    "id": "crag-fin-011",
    "query": "what are 3 examples of stocks that increased in value today?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "set",
    "expected_doc": "f627ded9.md",
    "expected_keywords": [
      "examples",
      "stocks",
      "increased",
      "value"
    ],
    "gold_answer": "here are 3 stocks that increased in value today. knsl, ttd, and coin"
  },
  {
    "id": "crag-fin-012",
    "query": "what were tesla's quarerly reported earnings per share for the fiscal year 2022?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "set",
    "expected_doc": "750fb046.md",
    "expected_keywords": [
      "quarerly",
      "reported",
      "earnings",
      "share",
      "fiscal"
    ],
    "gold_answer": "q1: $0.95, q2: $0.76, q3: $0.95, q4: $1.19"
  },
  {
    "id": "crag-fin-013",
    "query": "i'm looking for the p/e ratio of dks. would you happen to know what it is?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "simple",
    "expected_doc": "3325352c.md",
    "expected_keywords": [
      "looking",
      "ratio",
      "would",
      "happen"
    ],
    "gold_answer": "13.75"
  },
  {
    "id": "crag-fin-014",
    "query": "what was the volume of trading for colm on the most recent day that the market was open for trading?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "simple",
    "expected_doc": "4a1c8e19.md",
    "expected_keywords": [
      "volume",
      "trading",
      "recent",
      "market"
    ],
    "gold_answer": "464800"
  },
  {
    "id": "crag-fin-015",
    "query": "which companies had the three largest funding rounds of 2023?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "set",
    "expected_doc": "185c9898.md",
    "expected_keywords": [
      "which",
      "companies",
      "three",
      "largest",
      "funding"
    ],
    "gold_answer": "openai, stripe, anthropic"
  },
  {
    "id": "crag-fin-016",
    "query": "which company had the higher debt-to-equity ratio in 2023 between meta and microsoft?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "comparison",
    "expected_doc": "695151c2.md",
    "expected_keywords": [
      "which",
      "company",
      "higher",
      "ratio",
      "between"
    ],
    "gold_answer": "microsoft had a 0.29 debt-to-equity ratio in 2023, higher than meta's 0.24."
  },
  {
    "id": "crag-fin-017",
    "query": "what's auph's earnings per share?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "simple",
    "expected_doc": "03ef1484.md",
    "expected_keywords": [
      "earnings"
    ],
    "gold_answer": "0.4"
  },
  {
    "id": "crag-fin-018",
    "query": "what were the low and high prices of leco on the most recent trading day?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "simple_w_condition",
    "expected_doc": "426b244e.md",
    "expected_keywords": [
      "prices",
      "recent",
      "trading"
    ],
    "gold_answer": "$246.46, $250"
  },
  {
    "id": "crag-fin-019",
    "query": "how do the historical market capitalizations of coca-cola and pepsico  compare over the past decade?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "comparison",
    "expected_doc": "0d964457.md",
    "expected_keywords": [
      "historical",
      "market",
      "capitalizations",
      "pepsico",
      "compare"
    ],
    "gold_answer": "over the past decade, coca-cola has generally maintained a slightly higher market capitalization compared to pepsico."
  },
  {
    "id": "crag-fin-020",
    "query": "what are the different sectors of the european market?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "set",
    "expected_doc": "dfe6797a.md",
    "expected_keywords": [
      "different",
      "sectors",
      "european"
    ],
    "gold_answer": "agriculture, food & fisheries, electronic communications, energy & environment, financial services, information communication technologies, media, motor vehicles, pharmaceuticals & health services, transport & tourism"
  },
  {
    "id": "crag-fin-021",
    "query": "can you provide me with the most recent stock price of curo today?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "simple",
    "expected_doc": "6d6fcfb1.md",
    "expected_keywords": [
      "provide",
      "recent",
      "stock",
      "price"
    ],
    "gold_answer": "$0.24"
  },
  {
    "id": "crag-fin-022",
    "query": "is eli lilly and company's stock price up from its yearly open?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "simple_w_condition",
    "expected_doc": "13f718f3.md",
    "expected_keywords": [
      "lilly",
      "stock",
      "price",
      "yearly"
    ],
    "gold_answer": "yes, eli lilly and company is currently trading around $769 - higher than its yearly opening price of $592.72."
  },
  {
    "id": "crag-fin-023",
    "query": "how much do i pay in interest this month on a $2,000 credit card balance that has a simple annual interest rate is 14.99% per annum?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "post-processing",
    "expected_doc": "81e58a10.md",
    "expected_keywords": [
      "interest",
      "month",
      "credit",
      "balance",
      "simple"
    ],
    "gold_answer": "$24.98"
  },
  {
    "id": "crag-fin-024",
    "query": "which company distribute more dividends this year, muj or  tcbio?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "comparison",
    "expected_doc": "65d74002.md",
    "expected_keywords": [
      "which",
      "company",
      "distribute",
      "dividends"
    ],
    "gold_answer": "muj"
  },
  {
    "id": "crag-fin-025",
    "query": "what was sfwl's closing stock price on the most recent friday?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "simple",
    "expected_doc": "99e9659f.md",
    "expected_keywords": [
      "closing",
      "stock",
      "price",
      "recent"
    ],
    "gold_answer": "$1.76"
  },
  {
    "id": "crag-fin-026",
    "query": "which company has a higher return on assets, visa or mastercard?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "comparison",
    "expected_doc": "3ffcc157.md",
    "expected_keywords": [
      "which",
      "company",
      "higher",
      "return"
    ],
    "gold_answer": "as of the current financial data, visa has a higher return on assets than mastercard, with a return on assets of 23.63% compared to mastercard's 20.45%."
  },
  {
    "id": "crag-fin-027",
    "query": "what's the price-to-earnings ratio of ovbc as of now?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "simple",
    "expected_doc": "d4494e4f.md",
    "expected_keywords": [
      "ratio"
    ],
    "gold_answer": "i don't know"
  },
  {
    "id": "crag-fin-028",
    "query": "how much did funko open at today?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "simple",
    "expected_doc": "3c0f7c84.md",
    "expected_keywords": [
      "funko"
    ],
    "gold_answer": "$7.16"
  },
  {
    "id": "crag-fin-029",
    "query": "what's the closing stock price of hooker furnishings corporation on the last trading day?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "simple_w_condition",
    "expected_doc": "91fa191f.md",
    "expected_keywords": [
      "closing",
      "stock",
      "price",
      "hooker",
      "furnishings"
    ],
    "gold_answer": "$23.97"
  },
  {
    "id": "crag-fin-030",
    "query": "what is the total number of dividends that tnl has paid out in 2023?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "aggregation",
    "expected_doc": "b68c5239.md",
    "expected_keywords": [
      "total",
      "number",
      "dividends"
    ],
    "gold_answer": "4"
  },
  {
    "id": "crag-fin-031",
    "query": "what is the price-to-earnings ratio of pmtu",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "simple",
    "expected_doc": "6db497de.md",
    "expected_keywords": [
      "ratio"
    ],
    "gold_answer": "i don't know"
  },
  {
    "id": "crag-fin-032",
    "query": "what is treasury yield?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "simple",
    "expected_doc": "d669d968.md",
    "expected_keywords": [
      "treasury"
    ],
    "gold_answer": "treasury yield is the effective annual interest rate that the u.s. government pays on one of its debt obligations, expressed as a percentage."
  },
  {
    "id": "crag-fin-033",
    "query": "nep's current market cap.",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "simple",
    "expected_doc": "cead0ebe.md",
    "expected_keywords": [
      "current",
      "market"
    ],
    "gold_answer": "$2,543,205,863.73"
  },
  {
    "id": "crag-fin-034",
    "query": "which five states have successfully implemented universal healthcare program for all their residents?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "false_premise",
    "expected_doc": "001b3b84.md",
    "expected_keywords": [
      "which",
      "states",
      "successfully",
      "implemented",
      "universal"
    ],
    "gold_answer": "invalid question"
  },
  {
    "id": "crag-fin-035",
    "query": "on the day that cgi last paid dividends, what was the closing stock price?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "false_premise",
    "expected_doc": "425f5294.md",
    "expected_keywords": [
      "closing",
      "stock"
    ],
    "gold_answer": "invalid question"
  },
  {
    "id": "crag-fin-036",
    "query": "what was rmco's open price this past friday?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "simple",
    "expected_doc": "af7a2d0c.md",
    "expected_keywords": [
      "price"
    ],
    "gold_answer": "$1.24"
  },
  {
    "id": "crag-fin-037",
    "query": "what are the five types of financial markets?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "set",
    "expected_doc": "2bb77bcf.md",
    "expected_keywords": [
      "types",
      "financial"
    ],
    "gold_answer": "five types of financial markets are: stock market, bond market, foreign exchange market (forex), money market, commodities market"
  },
  {
    "id": "crag-fin-038",
    "query": "on average, what was the daily high stock price of xpev over the past week?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "simple",
    "expected_doc": "aee80084.md",
    "expected_keywords": [
      "daily",
      "stock",
      "price"
    ],
    "gold_answer": "$9.51"
  },
  {
    "id": "crag-fin-039",
    "query": "what's the open price for intellicheck today?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "simple",
    "expected_doc": "6dda642d.md",
    "expected_keywords": [
      "price",
      "intellicheck"
    ],
    "gold_answer": "$1.75"
  },
  {
    "id": "crag-fin-040",
    "query": "which company in the nasdaq 100 index has the highest ratio of green energy usage?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "multi-hop",
    "expected_doc": "53b47481.md",
    "expected_keywords": [
      "which",
      "company",
      "nasdaq",
      "index",
      "highest"
    ],
    "gold_answer": "the company with the highest percentage of renewable energy usage in the nasdaq 100 index is google (alphabet), with over 106% of its total power usage coming from green energy."
  },
  {
    "id": "crag-fin-041",
    "query": "what's the trading volume of mgrm on the last trading day?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "simple",
    "expected_doc": "20c10ddc.md",
    "expected_keywords": [
      "trading",
      "volume",
      "trading"
    ],
    "gold_answer": "27100"
  },
  {
    "id": "crag-fin-042",
    "query": "which company has a higher debt-to-equity ratio, autodesk or cdw?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "comparison",
    "expected_doc": "36db0540.md",
    "expected_keywords": [
      "which",
      "company",
      "higher",
      "autodesk"
    ],
    "gold_answer": "as of the current financial data, cdw has a higher debt-to-equity ratio than autodesk, with a debt-to-equity ratio of 3.07 compared to autodesk's 1.79."
  },
  {
    "id": "crag-fin-043",
    "query": "which day did eqix last distribute dividends to its shareholders?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "simple",
    "expected_doc": "47b7f5d4.md",
    "expected_keywords": [
      "which",
      "distribute",
      "dividends"
    ],
    "gold_answer": "2024-02-27"
  },
  {
    "id": "crag-fin-044",
    "query": "what is the most recent date that nml paid dividends to its shareholders?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "simple",
    "expected_doc": "23809175.md",
    "expected_keywords": [
      "recent",
      "dividends"
    ],
    "gold_answer": "2024-02-14"
  },
  {
    "id": "crag-fin-045",
    "query": "what is the trading volume of polypid on wed?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "simple_w_condition",
    "expected_doc": "5149dafc.md",
    "expected_keywords": [
      "trading",
      "volume",
      "polypid"
    ],
    "gold_answer": "2,500"
  },
  {
    "id": "crag-fin-046",
    "query": "what is the price of apple stock when they split the stock for the 10th time",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "false_premise",
    "expected_doc": "8e7bb686.md",
    "expected_keywords": [
      "price",
      "apple",
      "stock",
      "split",
      "stock"
    ],
    "gold_answer": "invalid question"
  },
  {
    "id": "crag-fin-047",
    "query": "on the last trading day, what were the daily low and high of nuw?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "simple_w_condition",
    "expected_doc": "473d18d5.md",
    "expected_keywords": [
      "trading",
      "daily"
    ],
    "gold_answer": "$13.83, $13.95"
  },
  {
    "id": "crag-fin-048",
    "query": "which five states had successfully implemented an hourly minimum wage of $18 or higher in 2023?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "false_premise",
    "expected_doc": "0c6a2eea.md",
    "expected_keywords": [
      "which",
      "states",
      "successfully",
      "implemented",
      "hourly"
    ],
    "gold_answer": "invalid question"
  },
  {
    "id": "crag-fin-049",
    "query": "what was the total value of all mergers and acquisitions (m&a) in the healthcare sector in 2018?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "simple_w_condition",
    "expected_doc": "5f76c5a2.md",
    "expected_keywords": [
      "total",
      "value",
      "mergers",
      "acquisitions",
      "healthcare"
    ],
    "gold_answer": "the total value of all m&a in the healthcare sector in 2020 was $235.1 billion."
  },
  {
    "id": "crag-fin-050",
    "query": "what's the latest stock price of oramed pharmaceuticals that's available?",
    "source": "qdrant",
    "category": "crag-finance",
    "question_type": "simple",
    "expected_doc": "032cf327.md",
    "expected_keywords": [
      "latest",
      "stock",
      "price",
      "oramed",
      "pharmaceuticals"
    ],
    "gold_answer": "$3.51"
  }
]

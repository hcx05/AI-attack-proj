# AI Agent 雙重攻擊向量研究：實驗架構、硬體配置與驗證計畫（優化版）

## 摘要

本研究聚焦於本地化 AI Agent 在多源資料整合與 RAG 檢索流程中的安全邊界問題。專題不以真實攻擊、資料外洩或破壞性操作為目的，而是建立一個封閉、可控、可重現的 AI Agent 安全靶場，用以驗證兩類核心風險：

1. **間接提示詞注入（Indirect Prompt Injection）**：不可信外部資料是否可能影響 Agent 的指令遵循、工具調用判斷與安全邊界。
2. **向量知識庫污染（Vector Store Poisoning）**：污染或錯誤資料是否可能在 RAG 檢索中取得過高排名，進而影響 Agent 的回答與決策。

本研究使用本地開源模型、容器化 Agent 環境、ChromaDB 向量資料庫與受限工具沙盒，評估 AI Agent 在面對不可信資料來源時的脆弱性，並提出對應的防禦加固策略。測試端採用**雙 Agent 攻擊模擬架構**：由 **Planner Agent（Qwen2.5-Instruct）** 負責策略規劃、實驗步驟拆解與 JSON 結構化輸出；由 **Payload Generator Agent（Llama-3.1-8B-Instruct）** 負責產生受控測試樣本與污染文本。兩者由 deterministic Python orchestrator 串接，避免完全自主化攻擊失控。

---

## 一、研究動機與問題定義

隨著 AI Agent 開始整合 WebFetch、File Reader、RAG、Shell 工具與企業知識庫，其安全風險已不再只來自模型本身，而是來自整個 LLM Pipeline 中的資料邊界、工具權限與外部記憶系統。

傳統軟體系統中，「資料」與「指令」通常有明確界線；然而在 LLM Agent 中，外部文件、網頁內容、使用者輸入與系統提示詞都可能被送入同一個上下文視窗。這使得不可信資料有機會影響 Agent 的推理流程與工具調用判斷。

因此，本研究提出一個雙重攻擊向量驗證架構，分析以下問題：

- Agent 是否能區分「外部資料內容」與「系統/開發者指令」？
- RAG 檢索層是否可能因污染資料而輸出錯誤或高風險建議？
- 工具調用權限是否能被不可信內容間接誘導？
- 容器化與沙盒是否足以防止資料層與決策層污染？
- 哪些防禦機制能有效降低上述風險？

---

## 二、研究範圍與安全邊界

本研究採取封閉式實驗設計，所有測試均在本地靶場中進行，不針對第三方系統、真實使用者資料或真實憑證進行測試。

### 2.1 實驗安全原則

- 所有敏感資訊均使用 **mock secret**、**canary token** 或假資料。
- Shell / Bash 工具僅允許執行白名單內的低風險指令。
- 網路連線預設關閉，必要時僅允許連至本地測試伺服器。
- 不進行真實憑證讀取、真實資料外傳、惡意下載或後門部署。
- 所有攻擊樣本只用於防禦驗證與風險觀察。
- 實驗結果以安全事件、檢索排名、工具調用意圖與防禦有效性為主，不以破壞性結果為目標。

### 2.2 研究定位

本專題定位為：

> **AI Agent 安全靶場與雙重資料層攻擊向量防禦驗證研究**

而非真實環境中的攻擊工具或自動化滲透系統。

---

## 三、核心實驗架構

本研究將原先複雜的多 Agent 自動攻擊拓撲收斂為雙向量安全驗證架構，但保留攻擊端的**雙 Agent 分工**：Planner Agent 負責策略與流程控制，Payload Generator Agent 負責生成可控測試樣本。

```text
        ┌─────────────────────────────────────────┐
        │          Attacker Simulator              │
        │ Planner Agent: Qwen2.5-Instruct          │
        │ Payload Generator: Llama-3.1-8B-Instruct │
        │ Deterministic Python Orchestrator        │
        └───────────────────┬─────────────────────┘
                            │
                            ▼
        ┌──────────────────────────────┐
        │     不可信外部資料來源        │
        │  HTML / Markdown / 文件內容   │
        └───────────────┬──────────────┘
                        │
                        ▼
        ┌──────────────────────────────┐
        │       NanoClaw-based Agent    │
        │ WebFetch / File Reader / RAG  │
        └───────┬──────────────┬───────┘
                │              │
                ▼              ▼
 ┌────────────────────┐   ┌────────────────────┐
 │ 向量一：間接提示注入 │   │ 向量二：RAG 知識污染 │
 │ 測試資料/指令邊界   │   │ 測試檢索與記憶可靠性 │
 └─────────┬──────────┘   └─────────┬──────────┘
           │                        │
           ▼                        ▼
 ┌────────────────────┐   ┌────────────────────┐
 │ 工具調用安全評估    │   │ 檢索排名與回答偏移評估 │
 └─────────┬──────────┘   └─────────┬──────────┘
           │                        │
           └────────────┬───────────┘
                        ▼
        ┌──────────────────────────────┐
        │       防禦策略與加固建議       │
        └──────────────────────────────┘
```

---

## 四、雙重攻擊向量設計

## 4.1 向量一：間接提示詞注入

### 研究問題

當 Agent 使用 WebFetch 或 File Reader 讀取外部資料時，外部內容是否可能被模型錯誤理解為高優先級指令，進而影響其回答、工具選擇或安全決策？

### 實驗設計

本階段建立受控外部資料來源，例如本地 HTML 頁面、Markdown 文件與測試用企業文件。這些資料中包含不同形式的高風險指令樣本，但樣本不執行真實攻擊，只用來測試 Agent 是否會出現以下行為：

- 忽略原有系統規則。
- 將外部資料誤判為系統指令。
- 產生不應出現的工具調用意圖。
- 嘗試存取 mock secret 或 canary token。
- 在安全提醒不足時輸出高風險操作建議。

### 驗證重點

- Agent 是否能正確標記外部資料為「不可信內容」。
- System prompt、tool policy 與資料內容之間的優先級是否清楚。
- 工具調用是否受到白名單、權限檢查與人工確認機制限制。
- 不同資料格式是否影響注入成功率，例如 HTML、Markdown、表格、圖片替代文字等。

### 預期產出

本階段不追求真實外洩，而是產出：

- 注入樣本類型分類。
- Agent 錯誤行為案例。
- 高風險工具調用意圖記錄。
- 防禦前後的安全行為比較。

---

## 4.2 向量二：向量知識庫污染

### 研究問題

在 RAG 系統中，若知識庫被加入錯誤、過期或惡意改寫的文件，是否會導致污染條目在特定查詢下被優先檢索，進而影響 Agent 的回答？

### 實驗設計

本階段建立一個小型企業知識庫，內容可包含：

- 密碼重設流程。
- 帳號權限申請流程。
- 內部 IT 支援流程。
- 財務或行政作業流程。
- 一般 FAQ 文件。

接著加入不同類型的污染文件，例如：

- 語意高度相似但內容錯誤的文件。
- 帶有過期流程的文件。
- 帶有誤導性建議的文件。
- 格式正常但內容可信度低的文件。

研究將比較正常文件與污染文件在不同查詢下的檢索排名、相似度分數與最終回答影響。

### 驗證重點

- 污染文件是否能進入 Top-k 檢索結果。
- 污染文件是否會改變 Agent 的最終回答。
- metadata filter、來源可信度標記、時間戳與審核狀態是否能降低污染影響。
- hybrid search、reranker 與安全分類器是否能改善檢索結果。
- Agent 是否會對低可信來源進行引用降權或安全提醒。

### 預期產出

本階段產出：

- 查詢語意與污染命中率分析。
- 正常文件與污染文件的檢索排名比較。
- RAG 回答偏移案例。
- 防禦機制前後的檢索品質比較。

---

## 五、系統與硬體配置

## 5.1 硬體環境

```text
實驗主機：
- CPU：AMD Ryzen Threadripper PRO
- RAM：128 GB
- GPU 0：NVIDIA RTX 4090 24 GB
- GPU 1：NVIDIA RTX 4080 SUPER 16 GB
- 作業系統：Linux / WSL2 / Docker 環境
```

本研究採用雙 GPU 分工設計，將受害者端與測試端隔離部署，降低不同推理任務之間的資源干擾。

---

## 5.2 藍軍靶機端：Victim Agent

### 部署內容

- Agent Framework：NanoClaw-based local agent
- 模型：Llama-3.1-8B-Instruct
- 推理方式：llama.cpp / llama-cpp-python / Ollama API
- 量化格式：GGUF Q4_K_M 或 Q5_K_M
- RAG：ChromaDB
- 工具：WebFetch、File Reader、受限 Shell Sandbox

### 顯存配置估計

| 項目 | 預估顯存 |
|---|---:|
| 8B GGUF 量化模型權重 | 約 4.8–6.0 GB |
| KV Cache（依 context length 與 cache precision 變動） | 約 1.5–5.0 GB |
| CUDA / runtime overhead | 約 1.0–2.0 GB |
| 預估總使用量 | 約 7.3–13.0 GB |

### 說明

RTX 4090 的 24 GB VRAM 對單一 8B 量化模型與中長上下文推理而言具備充足餘裕。實際使用量需以 `nvidia-smi`、llama.cpp runtime log 與推理框架記錄為準，不應只依靜態權重大小推估。

---

## 5.3 紅隊測試端：Dual-Agent Attacker Simulator

本研究的測試端不是單一模型，而是採用**雙 Agent 分工架構**。此設計可讓攻擊模擬流程更穩定，也能清楚區分「策略規劃」與「測試樣本生成」兩種任務。

### 部署內容

| 組件 | 模型 | 主要功能 | 部署建議 |
|---|---|---|---|
| **Planner Agent（攻擊大腦）** | Qwen2.5-3B-Instruct 或 Qwen2.5-7B-Instruct | 分析實驗目標、選擇測試方向、產生 JSON 格式計畫、判斷下一輪測試條件 | 優先使用 Qwen，因其結構化輸出與指令遵循能力較適合做流程控制 |
| **Payload Generator Agent（測試樣本生成器）** | Llama-3.1-8B-Instruct | 根據 Planner 的 JSON 指令產生受控 prompt injection 測試樣本、RAG 污染文本與不同格式變體 | 使用 Q6_K / Q8_0 GGUF 或其他高精度量化，以保留語意生成品質 |
| **Python Orchestrator** | 非 LLM 程式控制器 | 負責串接兩個 Agent、執行規則判定、記錄日誌、限制測試範圍 | 成功/失敗判定由程式規則控制，不完全交給 LLM 自主決策 |

### 顯存配置估計

| 項目 | 預估顯存 |
|---|---:|
| Planner：Qwen2.5-3B Q8 或 7B Q4/Q5 | 約 3.0–6.5 GB |
| Payload Generator：Llama-3.1-8B Q6/Q8 | 約 6.5–9.0 GB |
| KV Cache（4K–8K context，序列化推理） | 約 0.5–2.0 GB |
| CUDA / runtime overhead | 約 1.0–2.0 GB |
| 預估總使用量 | 約 10.0–15.5 GB |

### 說明

RTX 4080 SUPER 的 16 GB VRAM 可支援此雙 Agent 架構，但不建議讓兩個大型模型長時間同時高上下文常駐。較穩定的做法是採用**序列化推理**：先讓 Planner 產生 JSON 測試計畫，再釋放或暫停 Planner 資源，接著由 Payload Generator 根據該計畫產生測試樣本。若實際顯存壓力過高，可將 Planner 降為 Qwen2.5-3B，並將 Payload Generator 保持為 Llama-3.1-8B。

此處的 Attacker Simulator 僅用於封閉靶場中的安全測試樣本生成，不進行真實環境攻擊、真實資料外帶或破壞性操作。

---

## 六、模型與推理後端選擇

## 6.1 Victim Model

建議使用：

- Llama-3.1-8B-Instruct
- 量化格式：Q4_K_M / Q5_K_M
- 推理後端：llama.cpp 或 Ollama

選擇理由：

- 8B 模型可在消費級 GPU 上穩定部署。
- 具備長上下文能力，適合模擬多源資料輸入場景。
- 指令遵循能力足以模擬現代本地 AI Agent。
- 量化部署貼近中小型企業或個人本地化 Agent 使用情境。

## 6.2 Attacker Simulator Models

本研究將攻擊端明確拆分為兩個不同 Agent，而不是使用單一模型完成全部任務。

### 6.2.1 Planner Agent：Qwen2.5-Instruct

建議使用：

- Qwen2.5-3B-Instruct Q8_0
- 或 Qwen2.5-7B-Instruct Q4_K_M / Q5_K_M

角色定位：

- 作為攻擊模擬端的「大腦」。
- 負責讀取實驗目標與上一輪測試結果。
- 產生下一輪測試計畫。
- 使用嚴格 JSON schema 輸出策略，例如測試類型、資料格式、目標防禦機制、預期觀察項目。
- 不直接生成最終 payload，而是輸出可被 Payload Generator 執行的結構化任務。

選擇理由：

- Qwen 系列在 structured output、JSON 格式控制與指令遵循上較適合做流程規劃。
- 3B 版本可大幅降低 VRAM 壓力，適合放在 4080 SUPER 上與 8B Payload Generator 搭配。
- Planner 的任務重點是決策與格式穩定，不需要最大語意生成能力。

### 6.2.2 Payload Generator Agent：Llama-3.1-8B-Instruct

建議使用：

- Llama-3.1-8B-Instruct Q6_K
- 或 Llama-3.1-8B-Instruct Q8_0

角色定位：

- 作為攻擊模擬端的「測試樣本生成器」。
- 根據 Planner 輸出的 JSON 計畫，產生受控的 prompt injection 測試樣本。
- 產生不同資料格式的測試變體，例如 HTML、Markdown、FAQ 文件、RAG 污染文件。
- 產生語意相似但內容錯誤或低可信度的 RAG 測試文本。
- 不負責決定攻擊流程是否成功；成功/失敗判定交由 Python Orchestrator 與日誌規則處理。

選擇理由：

- Llama-3.1-8B 具備較強語意生成能力，適合生成自然、隱蔽但受控的測試文本。
- Q6/Q8 量化可減少語意退化，讓測試樣本更穩定。
- 與 Victim 同系列模型可測試「同族模型」在攻防語境下的行為差異，但兩者部署於不同 GPU 與不同角色中。

### 6.2.3 Orchestrator：Python Deterministic Controller

為避免完全自主化多 Agent 攻擊造成不可控風險，本研究使用 Python Orchestrator 作為硬性控制層：

- 控制 Planner 與 Payload Generator 的執行順序。
- 驗證 Planner JSON 是否符合 schema。
- 限制 Payload Generator 的輸出範圍。
- 將測試樣本送入 Victim Agent。
- 根據固定規則判定結果，例如是否出現不當工具調用意圖、污染文件是否進入 top-k。
- 記錄所有 prompt、response、tool decision 與 retrieval result。

此設計保留雙 Agent 的研究價值，同時避免將整個系統變成無限制自動化攻擊器。

## 6.3 後端一致性建議

若使用 GGUF，建議採用：

- llama.cpp
- llama-cpp-python
- Ollama

若使用 PyTorch / Transformers，則建議使用：

- FP16 / BF16
- bitsandbytes
- AWQ / GPTQ
- vLLM

本研究不建議在報告中同時宣稱「GGUF」與「原生 PyTorch/Transformers」為同一條部署路徑，避免技術表述混亂。

---

## 七、實驗階段計畫

## 7.1 階段一：Agent 靶場建置

### 目標

建立可重現、可觀測、可控的本地 AI Agent 測試環境。

### 任務

- 部署 NanoClaw-based local agent。
- 串接本地 Llama-3.1-8B-Instruct。
- 建立 WebFetch 與 File Reader 測試管線。
- 建立受限 Shell Sandbox。
- 設計 mock secret / canary token。
- 建立完整 logging 機制。

### 成功條件

- Agent 可讀取本地測試網頁與文件。
- Agent 可在受限政策下產生工具調用請求。
- 所有工具調用、模型輸入與模型輸出均可被記錄。
- 測試環境不接觸真實敏感資料。


---

## 7.2 階段二：雙 Agent 攻擊模擬端建置

### 目標

建立由 Planner Agent 與 Payload Generator Agent 組成的受控攻擊模擬端，使測試樣本生成流程具備可追蹤、可重現、可限制的特性。

### 任務

- 部署 Planner Agent：Qwen2.5-Instruct。
- 部署 Payload Generator Agent：Llama-3.1-8B-Instruct。
- 設計 Planner 的 JSON schema，例如 `test_type`、`target_vector`、`format`、`risk_level`、`expected_observation`。
- 設計 Payload Generator 的輸入模板，使其只能根據 Planner JSON 產生封閉靶場測試樣本。
- 使用 Python Orchestrator 串接 Planner、Payload Generator 與 Victim Agent。
- 加入輸出限制、日誌紀錄與安全檢查。

### 成功條件

- Planner 可穩定輸出合法 JSON。
- Payload Generator 可根據 JSON 產生對應測試樣本。
- Orchestrator 可阻擋不符合 schema 或超出安全範圍的輸出。
- 攻擊模擬端不接觸真實資料、不進行真實外部攻擊。

---

## 7.3 階段三：間接提示詞注入安全測試

### 目標

評估不可信外部資料是否會影響 Agent 的安全邊界。

### 任務

- 建立多類型測試文件。
- 設計不同強度的注入樣本。
- 測試 Agent 是否會遵守 system / developer policy。
- 記錄不當工具調用意圖。
- 比較不同防禦策略的效果。

### 成功條件

- 可重現至少數種注入風險情境。
- 可證明防禦前後 Agent 行為有差異。
- 可提出具體的資料隔離與工具權限加固建議。

---

## 7.4 階段四：RAG 向量知識庫污染測試

### 目標

評估污染文件對 RAG 檢索排名與最終回答的影響。

### 任務

- 建立乾淨知識庫 baseline。
- 加入不同類型污染文件。
- 比較 top-k retrieval 結果。
- 分析相似度分數與回答變化。
- 測試 metadata filter、trusted source label、reranker 等防禦方式。

### 成功條件

- 可觀察污染文件進入 top-k 的條件。
- 可證明污染文件會或不會影響最終回答。
- 可提出 RAG ingestion 與 retrieval 層面的安全建議。

---

## 7.5 階段五：雙向量聯動展示

### 目標

展示兩種風險如何在同一個 Agent pipeline 中互相放大，但不執行真實攻擊或破壞性操作。

### 任務

- 將間接提示注入與 RAG 污染放入同一靶場流程。
- 使用 mock secret 與 canary token 記錄安全邊界觸發情形。
- 比較單一風險與雙重風險下 Agent 行為差異。
- 整理防禦前後案例。

### 成功條件

- 可用封閉靶場演示雙向量風險。
- 可用日誌證明安全邊界是否被觸發。
- 可提出最小權限、資料標記、檢索審核與工具確認機制等防禦建議。

---

## 八、觀測與記錄項目

本研究將記錄以下資料：

| 類別 | 觀測項目 |
|---|---|
| 模型輸入 | system prompt、user prompt、retrieved context、tool result |
| 模型輸出 | final answer、tool call request、拒絕/遵守情況 |
| 工具調用 | tool name、arguments、policy decision、是否被 sandbox 阻擋 |
| RAG 檢索 | query、top-k results、similarity score、metadata、source trust |
| 系統資源 | VRAM、RAM、token count、context length、latency |
| 防禦結果 | 是否觸發 policy、是否需要人工確認、是否成功降權污染內容 |

---

## 九、防禦策略設計

本研究將比較以下防禦方式：

### 9.1 Prompt 與資料邊界防禦

- 明確標記外部資料為 untrusted content。
- 將外部資料包裹於固定格式中，禁止其被解讀為指令。
- 使用 system policy 明確規定資料內容不得覆蓋高層級指令。
- 對高風險工具調用加入二次確認。

### 9.2 工具權限防禦

- Shell 工具採用白名單指令。
- 對檔案讀取、環境變數、網路連線進行權限限制。
- 將工具調用分成 read-only、low-risk、high-risk 類別。
- 高風險 action 一律要求 human approval。
- 所有工具調用均進行 policy check 與 logging。

### 9.3 RAG 防禦

- 文件 ingestion 前進行來源驗證。
- 使用 metadata 標記來源、時間、審核狀態與可信度。
- 對低可信來源降權。
- 使用 hybrid search 與 reranker 檢查檢索結果。
- 對敏感流程類回答要求引用已審核文件。
- 對高風險建議加入安全提醒與拒絕規則。

---

## 十、預期成果

本專題預期產出：

1. 一個可重現的本地 AI Agent 安全靶場。
2. 一組間接提示詞注入測試案例。
3. 一組 RAG 知識庫污染測試案例。
4. 防禦前後 Agent 行為差異分析。
5. 硬體資源與推理穩定性記錄。
6. AI Agent 多源資料整合的安全設計建議。
7. 畢業專題展示用 demo、架構圖與實驗紀錄。

---

## 十一、專題可行性與風險控管

### 11.1 可行性

本專題已將原本的多 Agent 自動化攻擊鏈收斂為雙向量安全驗證，因此更符合大學畢業專題範圍。核心工作集中於：

- 本地 Agent 靶場建置。
- Prompt injection 防禦測試。
- 雙 Agent 攻擊模擬端建置：Planner 使用 Qwen，Payload Generator 使用 Llama。
- RAG 污染與檢索排名分析。
- 工具調用安全邊界驗證。

這些任務具有明確工程目標與可觀察輸出，適合作為 capstone project。

### 11.2 主要風險

| 風險 | 影響 | 緩解方式 |
|---|---|---|
| Agent 框架整合成本過高 | 延誤進度 | 先做最小可行靶場，再逐步接入 NanoClaw |
| 顯存估計不準 | OOM 或推理不穩 | 限制 context length、batch size、max tokens |
| 測試樣本太攻擊導向 | 倫理與審查風險 | 使用 mock data、封閉網路與防禦導向描述 |
| RAG 污染效果不穩 | 結果難重現 | 固定 embedding model、固定 top-k、固定 query set |
| LLM 行為隨機 | 成功率波動 | 固定 temperature、seed、prompt template |
| 報告語氣過強 | 專家質疑合理性 | 使用「風險驗證」與「防禦加固」語言 |

---

## 十二、結論

本研究以 AI Agent 在多源資料與 RAG 管線中的安全邊界為核心，聚焦於間接提示詞注入與向量知識庫污染兩項高風險問題。攻擊模擬端採用雙 Agent 分工：Planner Agent 使用 Qwen2.5-Instruct 負責策略規劃，Payload Generator Agent 使用 Llama-3.1-8B-Instruct 負責生成受控測試樣本。相較於完整自動化紅隊攻擊鏈，本版本更符合大學畢業專題的可完成性、倫理要求與展示需求。

本專題的價值不在於展示破壞性攻擊，而在於建立一個可控、可觀測、可重現的安全靶場，分析 AI Agent 在面對不可信資料來源時的失效模式，並提出可操作的防禦加固策略。

最終成果可定位為：

> **一套本地化 AI Agent 安全靶場與雙重資料層攻擊向量防禦驗證框架。**

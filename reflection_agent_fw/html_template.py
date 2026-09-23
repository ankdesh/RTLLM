"""Self-contained interactive HTML/JS visualization template for pipeline execution chains."""

HTML_TEMPLATE: str = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>RTLLM Pipeline Execution Visualizer</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  <style>
    :root {
      --bg: #0f172a;
      --card-bg: #1e293b;
      --card-border: #334155;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --accent: #38bdf8;
      --success: #22c55e;
      --failure: #ef4444;
      --warning: #f59e0b;
      --code-bg: #090d16;
    }
    body {
      background-color: var(--bg);
      color: var(--text);
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    .custom-scrollbar::-webkit-scrollbar {
      width: 6px;
      height: 6px;
    }
    .custom-scrollbar::-webkit-scrollbar-track {
      background: #1e293b;
    }
    .custom-scrollbar::-webkit-scrollbar-thumb {
      background: #475569;
      border-radius: 3px;
    }
  </style>
</head>
<body class="min-h-screen p-4 md:p-6 custom-scrollbar">
  <div class="max-w-7xl mx-auto space-y-6">

    <!-- Top Navigation & Run Header -->
    <header class="bg-[#1e293b] border border-[#334155] rounded-xl p-5 shadow-lg flex flex-col md:flex-row md:items-center md:justify-between gap-4">
      <div>
        <div class="flex items-center gap-2">
          <span class="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-sky-500/20 text-sky-400 border border-sky-500/30">
            RTLLM Pipeline Trace
          </span>
          <span id="run-framework-badge" class="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-purple-500/20 text-purple-400 border border-purple-500/30"></span>
        </div>
        <h1 class="text-xl md:text-2xl font-bold text-white mt-1 flex items-center gap-2">
          <span>⚡ Stage-Gated Pipeline Visualizer</span>
        </h1>
        <p id="run-meta-desc" class="text-xs md:text-sm text-slate-400 mt-0.5"></p>
      </div>

      <!-- Quick KPI Counters -->
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-2.5 sm:gap-3 text-center">
        <div class="bg-slate-900/60 border border-slate-700/60 rounded-lg px-3 py-2">
          <div class="text-xs text-slate-400">Total Designs</div>
          <div id="stat-total-designs" class="text-lg font-bold text-white">-</div>
        </div>
        <div class="bg-slate-900/60 border border-slate-700/60 rounded-lg px-3 py-2">
          <div class="text-xs text-slate-400">Solved Rate</div>
          <div id="stat-solve-rate" class="text-lg font-bold text-emerald-400">-</div>
        </div>
        <div class="bg-slate-900/60 border border-slate-700/60 rounded-lg px-3 py-2">
          <div class="text-xs text-slate-400">Total Stages</div>
          <div id="stat-total-stages" class="text-lg font-bold text-sky-400">-</div>
        </div>
        <div class="bg-slate-900/60 border border-slate-700/60 rounded-lg px-3 py-2">
          <div class="text-xs text-slate-400">Total Tokens</div>
          <div id="stat-total-tokens" class="text-lg font-bold text-amber-400">-</div>
        </div>
      </div>
    </header>

    <!-- Main Layout: Sidebar & Content -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">

      <!-- Left Column: Design Selector (4 cols) -->
      <aside class="lg:col-span-4 space-y-4">
        <div class="bg-[#1e293b] border border-[#334155] rounded-xl p-4 shadow">
          <div class="flex items-center justify-between mb-3">
            <h2 class="text-sm font-semibold uppercase tracking-wider text-slate-300">Benchmark Designs</h2>
            <span id="design-count-pill" class="text-xs bg-slate-800 text-slate-400 px-2 py-0.5 rounded-full"></span>
          </div>

          <input
            id="search-input"
            type="text"
            placeholder="Search design or tier..."
            class="w-full px-3 py-2 text-xs bg-slate-900 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500 mb-3"
            oninput="filterDesigns()"
          />

          <div id="design-list" class="space-y-1.5 max-h-[620px] overflow-y-auto custom-scrollbar pr-1">
            <!-- Dynamic Design Buttons -->
          </div>
        </div>
      </aside>

      <!-- Right Column: Visual Stage Chain (8 cols) -->
      <main class="lg:col-span-8 space-y-5">
        <!-- Selected Design Status Banner -->
        <div id="design-banner" class="bg-[#1e293b] border border-[#334155] rounded-xl p-4 flex flex-wrap items-center justify-between gap-3 shadow">
          <div class="flex items-center gap-3">
            <div id="banner-status-icon" class="w-10 h-10 rounded-xl flex items-center justify-center font-bold text-lg"></div>
            <div>
              <div class="flex items-center gap-2">
                <h2 id="banner-design-name" class="text-lg font-bold text-white"></h2>
                <span id="banner-tier-badge" class="px-2 py-0.5 text-xs font-medium rounded-full bg-slate-800 text-slate-300"></span>
              </div>
              <p id="banner-category" class="text-xs text-slate-400"></p>
            </div>
          </div>

          <div class="flex items-center gap-3 text-xs">
            <div class="text-right">
              <span class="text-slate-400 block">Solve Level</span>
              <span id="banner-solved-level" class="font-bold text-white"></span>
            </div>
            <div class="h-6 w-px bg-slate-700"></div>
            <div class="text-right">
              <span class="text-slate-400 block">Compute</span>
              <span id="banner-tokens" class="font-semibold text-slate-200"></span>
            </div>
            <div class="h-6 w-px bg-slate-700"></div>
            <div class="text-right">
              <span class="text-slate-400 block">Latency</span>
              <span id="banner-latency" class="font-semibold text-slate-200"></span>
            </div>
          </div>
        </div>

        <!-- Stage Timeline Chain Container -->
        <div class="bg-[#1e293b] border border-[#334155] rounded-xl p-5 shadow space-y-6">
          <div class="flex items-center justify-between border-b border-slate-700 pb-3">
            <div>
              <h3 class="font-semibold text-white text-base">Execution Stage Chain</h3>
              <p class="text-xs text-slate-400">Click any stage block in the pipeline to inspect full inputs, generated code, and tool logs.</p>
            </div>
            <span class="text-xs px-2.5 py-1 bg-slate-800 text-sky-400 border border-slate-700 rounded-md">
              Interactive Inspector
            </span>
          </div>

          <!-- Dynamic Rounds Container -->
          <div id="rounds-container" class="space-y-6">
            <!-- Dynamic round cards -->
          </div>
        </div>

        <!-- Inspector Drawer / Modal -->
        <div id="inspector-card" class="bg-[#1e293b] border border-[#334155] rounded-xl p-5 shadow space-y-4 hidden">
          <div class="flex items-center justify-between border-b border-slate-700 pb-3">
            <div class="flex items-center gap-3">
              <span id="inspector-stage-badge" class="px-2.5 py-1 text-xs font-semibold rounded-md"></span>
              <h3 id="inspector-stage-title" class="font-bold text-white text-base"></h3>
            </div>
            <button onclick="closeInspector()" class="text-slate-400 hover:text-white text-sm font-semibold px-2 py-1 rounded bg-slate-800 hover:bg-slate-700">
              ✕ Close
            </button>
          </div>

          <!-- Inspector Tabs -->
          <div class="flex items-center gap-2 border-b border-slate-700 pb-2 text-xs">
            <button id="tab-btn-code" onclick="switchInspectorTab('code')" class="px-3 py-1.5 rounded-lg bg-sky-600 text-white font-medium">
              Extracted RTL Code
            </button>
            <button id="tab-btn-diagnostics" onclick="switchInspectorTab('diagnostics')" class="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700">
              Diagnostics / Tool Output
            </button>
            <button id="tab-btn-prompt" onclick="switchInspectorTab('prompt')" class="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700">
              Prompt Context
            </button>
            <button id="tab-btn-telemetry" onclick="switchInspectorTab('telemetry')" class="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700">
              Telemetry & Metrics
            </button>
          </div>

          <!-- Tab Contents -->
          <div id="tab-content-code" class="space-y-2">
            <div class="flex justify-between items-center text-xs text-slate-400">
              <span>Verilog Source (Synthesizable RTL)</span>
              <button onclick="copyCode()" class="text-xs bg-slate-800 hover:bg-slate-700 text-sky-400 px-2 py-1 rounded border border-slate-700">
                Copy Code
              </button>
            </div>
            <pre id="inspector-code-block" class="bg-[#090d16] text-slate-200 p-4 rounded-lg text-xs font-mono overflow-x-auto max-h-[420px] custom-scrollbar border border-slate-800"></pre>
          </div>

          <div id="tab-content-diagnostics" class="space-y-2 hidden">
            <div class="text-xs text-slate-400">Compiler, Linter, or Testbench Output</div>
            <pre id="inspector-diag-block" class="bg-[#090d16] text-amber-300 p-4 rounded-lg text-xs font-mono overflow-x-auto max-h-[420px] custom-scrollbar border border-slate-800"></pre>
          </div>

          <div id="tab-content-prompt" class="space-y-2 hidden">
            <div class="text-xs text-slate-400">LLM System & User Prompt Messages</div>
            <pre id="inspector-prompt-block" class="bg-[#090d16] text-slate-300 p-4 rounded-lg text-xs font-mono overflow-x-auto max-h-[420px] custom-scrollbar border border-slate-800 whitespace-pre-wrap"></pre>
          </div>

          <div id="tab-content-telemetry" class="space-y-3 hidden">
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              <div class="bg-slate-900 p-3 rounded-lg border border-slate-800">
                <span class="text-slate-400 block">Duration</span>
                <span id="tel-duration" class="font-bold text-white text-sm"></span>
              </div>
              <div class="bg-slate-900 p-3 rounded-lg border border-slate-800">
                <span class="text-slate-400 block">Prompt Tokens</span>
                <span id="tel-ptokens" class="font-bold text-white text-sm"></span>
              </div>
              <div class="bg-slate-900 p-3 rounded-lg border border-slate-800">
                <span class="text-slate-400 block">Comp Tokens</span>
                <span id="tel-ctokens" class="font-bold text-white text-sm"></span>
              </div>
              <div class="bg-slate-900 p-3 rounded-lg border border-slate-800">
                <span class="text-slate-400 block">Status</span>
                <span id="tel-status" class="font-bold text-sm"></span>
              </div>
            </div>
            <pre id="inspector-raw-json" class="bg-[#090d16] text-slate-400 p-4 rounded-lg text-xs font-mono overflow-x-auto max-h-[250px] custom-scrollbar border border-slate-800"></pre>
          </div>
        </div>

      </main>
    </div>

  </div>

  <script>
    // Embedded Data injected by Python generator
    const RUN_DATA = %DATA_JSON%;

    let selectedDesignName = null;
    let selectedStageData = null;

    function init() {
      // 1. Render Header Meta
      const manifest = RUN_DATA.manifest || {};
      document.getElementById('run-framework-badge').textContent = manifest.framework || 'Agent Pipeline';
      document.getElementById('run-meta-desc').textContent = 
        `Model: ${manifest.model || 'Unknown'} | Start: ${manifest.start_time || 'N/A'} | Max Rounds: ${manifest.max_rounds || 5}`;

      // 2. Render Global Stats
      const designs = RUN_DATA.designs || [];
      const solvedCount = designs.filter(d => d.solved).length;
      document.getElementById('stat-total-designs').textContent = designs.length;
      document.getElementById('stat-solve-rate').textContent = 
        designs.length ? `${((solvedCount / designs.length) * 100).toFixed(1)}%` : '0%';

      let totalStages = 0;
      let totalTokens = 0;
      designs.forEach(d => {
        totalTokens += (d.total_prompt_tokens || 0) + (d.total_completion_tokens || 0);
        (d.steps || []).forEach(s => {
          totalStages += (s.stages || []).length || 3;
        });
      });
      document.getElementById('stat-total-stages').textContent = totalStages;
      document.getElementById('stat-total-tokens').textContent = totalTokens.toLocaleString();

      // 3. Render Design List
      renderDesignList(designs);

      // 4. Select first design by default
      if (designs.length > 0) {
        selectDesign(designs[0].design_name);
      }
    }

    function renderDesignList(designs) {
      const container = document.getElementById('design-list');
      container.innerHTML = '';
      document.getElementById('design-count-pill').textContent = `${designs.length} designs`;

      designs.forEach(d => {
        const btn = document.createElement('button');
        btn.id = `btn-design-${d.design_name}`;
        btn.className = `w-full text-left p-2.5 rounded-lg border transition-all text-xs flex items-center justify-between ${
          d.design_name === selectedDesignName 
            ? 'bg-sky-950/60 border-sky-500 text-white shadow-sm' 
            : 'bg-slate-900/60 border-slate-800 text-slate-300 hover:bg-slate-800/80 hover:border-slate-700'
        }`;
        btn.onclick = () => selectDesign(d.design_name);

        const statusPill = d.solved
          ? `<span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">${d.solved_level || 'PASS'}</span>`
          : `<span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-500/20 text-rose-400 border border-rose-500/30">FAIL</span>`;

        btn.innerHTML = `
          <div class="truncate mr-2">
            <span class="font-semibold block truncate">${d.design_name}</span>
            <span class="text-[10px] text-slate-400">Tier ${d.tier || 1} • ${d.category}</span>
          </div>
          <div>${statusPill}</div>
        `;
        container.appendChild(btn);
      });
    }

    function filterDesigns() {
      const query = document.getElementById('search-input').value.toLowerCase();
      const designs = RUN_DATA.designs || [];
      const filtered = designs.filter(d => 
        d.design_name.toLowerCase().includes(query) ||
        (d.category && d.category.toLowerCase().includes(query)) ||
        `tier ${d.tier}`.includes(query)
      );
      renderDesignList(filtered);
    }

    function selectDesign(name) {
      selectedDesignName = name;
      const design = (RUN_DATA.designs || []).find(d => d.design_name === name);
      if (!design) return;

      // Update button styling
      document.querySelectorAll('#design-list button').forEach(b => {
        b.classList.remove('bg-sky-950/60', 'border-sky-500', 'text-white');
        b.classList.add('bg-slate-900/60', 'border-slate-800', 'text-slate-300');
      });
      const activeBtn = document.getElementById(`btn-design-${name}`);
      if (activeBtn) {
        activeBtn.classList.add('bg-sky-950/60', 'border-sky-500', 'text-white');
        activeBtn.classList.remove('bg-slate-900/60', 'border-slate-800', 'text-slate-300');
      }

      // Update Banner
      document.getElementById('banner-design-name').textContent = design.design_name;
      document.getElementById('banner-tier-badge').textContent = `Tier ${design.tier || 1}`;
      document.getElementById('banner-category').textContent = `${design.category} • ${design.subcategory || ''}`;

      const iconDiv = document.getElementById('banner-status-icon');
      if (design.solved) {
        iconDiv.className = 'w-10 h-10 rounded-xl flex items-center justify-center font-bold text-lg bg-emerald-500/20 text-emerald-400 border border-emerald-500/30';
        iconDiv.textContent = '✓';
      } else {
        iconDiv.className = 'w-10 h-10 rounded-xl flex items-center justify-center font-bold text-lg bg-rose-500/20 text-rose-400 border border-rose-500/30';
        iconDiv.textContent = '✕';
      }

      document.getElementById('banner-solved-level').textContent = design.solved ? (design.solved_level || 'SOLVED') : 'EXHAUSTED';
      document.getElementById('banner-tokens').textContent = `${((design.total_prompt_tokens||0)+(design.total_completion_tokens||0)).toLocaleString()} tok`;
      document.getElementById('banner-latency').textContent = `${(design.total_elapsed_sec || 0).toFixed(2)}s`;

      // Render Stage Chain Rounds
      renderRounds(design);
      closeInspector();
    }

    function renderRounds(design) {
      const container = document.getElementById('rounds-container');
      container.innerHTML = '';

      const steps = design.steps || [];
      if (steps.length === 0) {
        container.innerHTML = `<div class="p-6 text-center text-slate-400 text-sm">No stage steps recorded for this design.</div>`;
        return;
      }

      steps.forEach((step, idx) => {
        const roundCard = document.createElement('div');
        roundCard.className = 'border border-slate-700/80 rounded-xl p-4 bg-slate-900/40 space-y-3';

        const roundHeader = `
          <div class="flex items-center justify-between text-xs pb-2 border-b border-slate-800">
            <div class="flex items-center gap-2">
              <span class="font-bold text-white text-sm">Iteration ${idx + 1}</span>
              <span class="px-2 py-0.5 rounded font-mono text-[11px] bg-slate-800 text-sky-400 border border-slate-700">${step.level}</span>
            </div>
            <div class="text-slate-400">
              <span>${(step.elapsed_sec || 0).toFixed(2)}s</span> • 
              <span>${((step.prompt_tokens||0)+(step.completion_tokens||0))} tok</span>
            </div>
          </div>
        `;

        // Stages in this step
        let stages = step.stages;
        if (!stages || stages.length === 0) {
          stages = [
            {
              stage_id: 'prompt_prep',
              stage_name: 'Prompt Assembly',
              status: 'SUCCESS',
              duration_sec: 0.01,
              inputs: { level: step.level },
              outputs: { prompt_chars: (step.prompt || '').length }
            },
            {
              stage_id: 'rtl_generation',
              stage_name: 'RTL Code Generation',
              status: step.extracted_code ? 'SUCCESS' : 'FAILURE',
              duration_sec: step.elapsed_sec ? step.elapsed_sec * 0.8 : 1.0,
              inputs: { model: 'LLM' },
              outputs: { extracted_code: step.extracted_code, completion: step.completion },
              metrics: { prompt_tokens: step.prompt_tokens, completion_tokens: step.completion_tokens }
            },
            {
              stage_id: 'static_lint',
              stage_name: 'Verilator Static Lint',
              status: step.lint_ok ? 'SUCCESS' : 'FAILURE',
              duration_sec: 0.01,
              inputs: {},
              outputs: { lint_output: step.lint_output, lint_ok: step.lint_ok }
            },
            {
              stage_id: 'behavioral_sim',
              stage_name: 'Icarus Verilog Simulation',
              status: step.lint_ok ? (step.sim_ok ? 'SUCCESS' : 'FAILURE') : 'SKIPPED',
              duration_sec: step.lint_ok ? 0.15 : 0.0,
              inputs: {},
              outputs: { sim_output: step.sim_output, sim_ok: step.sim_ok }
            },
            {
              stage_id: 'reflection_decision',
              stage_name: 'Reflection Decision',
              status: step.sim_ok ? 'SUCCESS' : 'RETRY',
              duration_sec: 0.001,
              inputs: {},
              outputs: { decision: step.sim_ok ? 'SOLVED' : 'REFLECT' }
            }
          ];
        }

        const stagesGrid = document.createElement('div');
        stagesGrid.className = 'grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3 pt-1';

        stages.forEach(st => {
          const node = document.createElement('div');
          let statusBg = 'bg-slate-800/80 border-slate-700 text-slate-300';
          let badgeBg = 'bg-slate-700 text-slate-300';
          let statusText = st.status;

          if (st.status === 'SUCCESS') {
            statusBg = 'bg-emerald-950/30 border-emerald-500/50 text-emerald-300 hover:border-emerald-400';
            badgeBg = 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30';
          } else if (st.status === 'FAILURE' || st.status === 'TIMEOUT') {
            statusBg = 'bg-rose-950/30 border-rose-500/50 text-rose-300 hover:border-rose-400';
            badgeBg = 'bg-rose-500/20 text-rose-400 border border-rose-500/30';
          } else if (st.status === 'SKIPPED') {
            statusBg = 'bg-slate-900/40 border-slate-800 text-slate-500 opacity-60';
            badgeBg = 'bg-slate-800 text-slate-500';
          } else if (st.status === 'RETRY') {
            statusBg = 'bg-amber-950/30 border-amber-500/50 text-amber-300 hover:border-amber-400';
            badgeBg = 'bg-amber-500/20 text-amber-400 border border-amber-500/30';
          }

          node.className = `p-3 rounded-lg border transition-all cursor-pointer shadow-sm relative hover:scale-[1.02] ${statusBg}`;
          node.onclick = () => openInspector(st, step);

          node.innerHTML = `
            <div class="flex items-center justify-between mb-1.5">
              <span class="text-[10px] font-mono px-1.5 py-0.5 rounded ${badgeBg}">${statusText}</span>
              <span class="text-[10px] text-slate-400 font-mono">${(st.duration_sec || 0).toFixed(2)}s</span>
            </div>
            <div class="font-semibold text-xs text-white truncate">${st.stage_name}</div>
            <div class="text-[10px] text-slate-400 mt-1 truncate">
              ${st.stage_id === 'rtl_generation' ? `${st.metrics?.prompt_tokens || 0}+${st.metrics?.completion_tokens || 0} tok` : (st.error_message || 'Inspect logs')}
            </div>
          `;
          stagesGrid.appendChild(node);
        });

        roundCard.innerHTML = roundHeader;
        roundCard.appendChild(stagesGrid);
        container.appendChild(roundCard);
      });
    }

    function openInspector(stage, step) {
      selectedStageData = { stage, step };
      const card = document.getElementById('inspector-card');
      card.classList.remove('hidden');

      document.getElementById('inspector-stage-title').textContent = stage.stage_name;
      const badge = document.getElementById('inspector-stage-badge');
      badge.textContent = stage.status;
      badge.className = `px-2.5 py-1 text-xs font-semibold rounded-md ${
        stage.status === 'SUCCESS' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
        stage.status === 'FAILURE' ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30' :
        'bg-slate-800 text-slate-400'
      }`;

      // Populate Code
      const code = stage.outputs?.extracted_code || step.extracted_code || '// No Verilog emitted in this stage';
      document.getElementById('inspector-code-block').textContent = code;

      // Populate Diagnostics
      const diag = stage.outputs?.lint_output || stage.outputs?.sim_output || step.lint_output || step.sim_output || stage.error_message || 'No diagnostic errors reported.';
      document.getElementById('inspector-diag-block').textContent = diag;

      // Populate Prompt
      const prompt = step.prompt || JSON.stringify(stage.inputs || {}, null, 2);
      document.getElementById('inspector-prompt-block').textContent = prompt;

      // Populate Telemetry
      document.getElementById('tel-duration').textContent = `${(stage.duration_sec || 0).toFixed(4)}s`;
      document.getElementById('tel-ptokens').textContent = stage.metrics?.prompt_tokens || step.prompt_tokens || 0;
      document.getElementById('tel-ctokens').textContent = stage.metrics?.completion_tokens || step.completion_tokens || 0;
      const telStatus = document.getElementById('tel-status');
      telStatus.textContent = stage.status;
      telStatus.className = `font-bold text-sm ${stage.status === 'SUCCESS' ? 'text-emerald-400' : 'text-rose-400'}`;

      document.getElementById('inspector-raw-json').textContent = JSON.stringify(stage, null, 2);

      // Default to appropriate tab
      if (stage.stage_id === 'static_lint' || stage.stage_id === 'behavioral_sim') {
        switchInspectorTab('diagnostics');
      } else {
        switchInspectorTab('code');
      }

      card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    function closeInspector() {
      document.getElementById('inspector-card').classList.add('hidden');
    }

    function switchInspectorTab(tab) {
      const tabs = ['code', 'diagnostics', 'prompt', 'telemetry'];
      tabs.forEach(t => {
        const btn = document.getElementById(`tab-btn-${t}`);
        const content = document.getElementById(`tab-content-${t}`);
        if (t === tab) {
          btn.className = 'px-3 py-1.5 rounded-lg bg-sky-600 text-white font-medium';
          content.classList.remove('hidden');
        } else {
          btn.className = 'px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700';
          content.classList.add('hidden');
        }
      });
    }

    function copyCode() {
      const code = document.getElementById('inspector-code-block').textContent;
      navigator.clipboard.writeText(code).then(() => {
        alert('RTL code copied to clipboard!');
      });
    }

    window.onload = init;
  </script>
</body>
</html>
"""

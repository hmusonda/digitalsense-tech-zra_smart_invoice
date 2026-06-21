frappe.pages["zra-setup-wizard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "ZRA Smart Invoice Setup",
		single_column: true,
	});

	page.main.html(`
<div class="zra-wizard container" style="max-width:700px;margin:30px auto;">

  <!-- Progress steps -->
  <div class="zra-steps" style="display:flex;justify-content:space-between;margin-bottom:30px;">
    ${["Credentials", "Test Connection", "Initialize Device", "Done"].map((s, i) => `
      <div class="zra-step" id="step-indicator-${i}" style="flex:1;text-align:center;padding:8px;border-bottom:3px solid #ddd;color:#aaa;font-size:12px;">
        <div style="font-size:18px;font-weight:bold;">${i + 1}</div>${s}
      </div>`).join("")}
  </div>

  <!-- Step 0: Credentials -->
  <div class="zra-panel" id="panel-0">
    <h3 style="margin-bottom:16px;">Step 1 — Enter ZRA Credentials</h3>
    <p style="color:#666;margin-bottom:20px;">
      These credentials are provided by ZRA when you register on the
      <a href="https://www.zra.org.zm/smart-invoice-learn-more/" target="_blank">Smart Invoice Taxpayer Portal</a>.
    </p>
    <div class="form-group"><label>TPIN <span style="color:red">*</span></label>
      <input type="text" id="wiz-tpin" class="form-control" placeholder="e.g. 1234567890" /></div>
    <div class="form-group" style="margin-top:12px;"><label>Branch ID <span style="color:red">*</span></label>
      <input type="text" id="wiz-branch" class="form-control" placeholder="e.g. 000" /></div>
    <div class="form-group" style="margin-top:12px;"><label>Device Serial Number <span style="color:red">*</span></label>
      <input type="text" id="wiz-serial" class="form-control" placeholder="e.g. VSDC-2024-XXXX" /></div>
    <div class="form-group" style="margin-top:12px;"><label>DigiTax API Key <span style="color:red">*</span></label>
      <input type="password" id="wiz-apikey" class="form-control" placeholder="Your DigiTax API key" /></div>
    <div class="form-group" style="margin-top:12px;"><label>Environment <span style="color:red">*</span></label>
      <select id="wiz-env" class="form-control">
        <option value="Sandbox">Sandbox (testing)</option>
        <option value="Production">Production</option>
      </select></div>
    <div style="margin-top:20px;">
      <button class="btn btn-primary" id="btn-save-creds">Save & Continue →</button>
    </div>
  </div>

  <!-- Step 1: Test Connection -->
  <div class="zra-panel" id="panel-1" style="display:none;">
    <h3 style="margin-bottom:16px;">Step 2 — Test Connection to DigiTax</h3>
    <p style="color:#666;margin-bottom:20px;">
      We'll verify that your DigiTax API key is valid and that the server can reach the DigiTax API.
    </p>
    <div id="conn-status" style="padding:16px;border-radius:4px;background:#f5f5f5;margin-bottom:16px;">
      Click the button below to test the connection.
    </div>
    <button class="btn btn-primary" id="btn-test-conn">Test Connection</button>
    <button class="btn btn-default" id="btn-back-0" style="margin-left:8px;">← Back</button>
  </div>

  <!-- Step 2: Initialize Device -->
  <div class="zra-panel" id="panel-2" style="display:none;">
    <h3 style="margin-bottom:16px;">Step 3 — Initialize Device with ZRA</h3>
    <p style="color:#666;margin-bottom:20px;">
      This sends your device registration to ZRA via DigiTax. It only needs to be done <strong>once per site</strong>.
      After this, invoices will be submitted automatically.
    </p>
    <div id="init-status" style="padding:16px;border-radius:4px;background:#f5f5f5;margin-bottom:16px;">
      Ready to initialize.
    </div>
    <button class="btn btn-primary btn-lg" id="btn-init-device">Initialize Device with ZRA</button>
    <button class="btn btn-default" id="btn-back-1" style="margin-left:8px;">← Back</button>
  </div>

  <!-- Step 3: Done -->
  <div class="zra-panel" id="panel-3" style="display:none;">
    <div style="text-align:center;padding:40px 20px;">
      <div style="font-size:60px;">✅</div>
      <h2 style="margin:16px 0 8px;">ZRA Smart Invoice is Active</h2>
      <p style="color:#666;max-width:400px;margin:0 auto 24px;">
        This site is registered with ZRA. All submitted Sales Invoices will now be
        automatically transmitted to ZRA Smart Invoice System in real time.
      </p>
      <a href="/app/zra-settings" class="btn btn-default" style="margin-right:8px;">View ZRA Settings</a>
      <a href="/app/sales-invoice/new" class="btn btn-primary">Create First Invoice</a>
    </div>
  </div>

  <!-- Dashboard summary (shown when already initialized) -->
  <div id="zra-dashboard" style="display:none;margin-top:30px;padding:20px;border:1px solid #ddd;border-radius:6px;">
    <h4>ZRA Submission Health</h4>
    <div style="display:flex;gap:16px;margin-top:12px;" id="zra-health-cards"></div>
  </div>

</div>
`);

	// ── Helpers ──────────────────────────────────────────────────────────────
	const $ = (id) => document.getElementById(id);
	let currentStep = 0;

	function showStep(n) {
		[0, 1, 2, 3].forEach((i) => {
			$(`panel-${i}`).style.display = i === n ? "block" : "none";
			const ind = $(`step-indicator-${i}`);
			ind.style.borderBottomColor = i < n ? "#5cb85c" : i === n ? "#337ab7" : "#ddd";
			ind.style.color = i <= n ? "#333" : "#aaa";
		});
		currentStep = n;
	}

	function setStatus(elId, msg, type = "info") {
		const colours = { info: "#d9edf7", success: "#dff0d8", error: "#f2dede" };
		const el = $(elId);
		el.style.background = colours[type] || colours.info;
		el.innerHTML = msg;
	}

	// ── Load existing settings ────────────────────────────────────────────────
	frappe.call({
		method: "frappe.client.get_single_value",
		args: { doctype: "ZRA Settings", field: "is_initialized" },
		callback(r) {
			if (r.message) {
				// Already set up — show dashboard
				showStep(3);
				loadDashboard();
			} else {
				showStep(0);
			}
		},
	});

	function loadDashboard() {
		$("zra-dashboard").style.display = "block";
		frappe.call({
			method: "zra_smart_invoice.zra_smart_invoice.api.whitelisted.get_zra_status",
			callback(r) {
				if (!r.message) return;
				const d = r.message;
				$("zra-health-cards").innerHTML = [
					["Total Submissions", d.total, "#337ab7"],
					["Success", d.success, "#5cb85c"],
					["Failed", d.failed, "#d9534f"],
					["Pending", d.pending, "#f0ad4e"],
				].map(([label, val, colour]) => `
					<div style="flex:1;text-align:center;padding:16px;border-radius:6px;background:${colour};color:#fff;">
						<div style="font-size:28px;font-weight:bold;">${val}</div>
						<div style="font-size:11px;margin-top:4px;">${label}</div>
					</div>`).join("");
			},
		});
	}

	// ── Step 0: Save credentials ──────────────────────────────────────────────
	$("btn-save-creds").onclick = function () {
		const tpin   = $("wiz-tpin").value.trim();
		const branch = $("wiz-branch").value.trim();
		const serial = $("wiz-serial").value.trim();
		const apikey = $("wiz-apikey").value.trim();
		const env    = $("wiz-env").value;

		if (!tpin || !branch || !serial || !apikey) {
			frappe.msgprint("Please fill in all required fields.");
			return;
		}

		frappe.call({
			method: "frappe.client.set_value",
			args: {
				doctype: "ZRA Settings",
				name: "ZRA Settings",
				fieldname: { tpin, branch_id: branch, device_serial_no: serial, environment: env },
			},
			callback() {
				// Save API key separately (password field)
				frappe.call({
					method: "frappe.client.set_value",
					args: {
						doctype: "ZRA Settings",
						name: "ZRA Settings",
						fieldname: { digitax_api_key: apikey },
					},
					callback() { showStep(1); },
				});
			},
		});
	};

	// ── Step 1: Test connection ───────────────────────────────────────────────
	$("btn-test-conn").onclick = function () {
		setStatus("conn-status", "⏳ Testing connection to DigiTax API...", "info");
		$("btn-test-conn").disabled = true;

		frappe.call({
			method: "zra_smart_invoice.zra_smart_invoice.api.whitelisted.test_connection",
			callback(r) {
				$("btn-test-conn").disabled = false;
				if (r.exc) {
					setStatus("conn-status", `❌ Connection failed: ${r.exc}`, "error");
				} else {
					setStatus("conn-status", "✅ Connection successful! DigiTax API is reachable.", "success");
					setTimeout(() => showStep(2), 1200);
				}
			},
		});
	};

	$("btn-back-0").onclick = () => showStep(0);

	// ── Step 2: Initialize device ─────────────────────────────────────────────
	$("btn-init-device").onclick = function () {
		setStatus("init-status", "⏳ Sending device initialization to ZRA via DigiTax...", "info");
		$("btn-init-device").disabled = true;

		frappe.call({
			method: "zra_smart_invoice.zra_smart_invoice.api.whitelisted.initialize_device",
			freeze: true,
			freeze_message: "Initializing with ZRA — please wait...",
			callback(r) {
				$("btn-init-device").disabled = false;
				if (r.exc || (r.message && r.message.resultCd && r.message.resultCd !== "000")) {
					const err = (r.message && r.message.resultMsg) || r.exc || "Unknown error";
					setStatus("init-status", `❌ Initialization failed: ${err}`, "error");
				} else {
					setStatus("init-status", "✅ Device successfully registered with ZRA!", "success");
					setTimeout(() => { showStep(3); loadDashboard(); }, 1200);
				}
			},
		});
	};

	$("btn-back-1").onclick = () => showStep(1);
};

(() => {
  "use strict";

  const root = document.querySelector(".field-page");
  const form = document.getElementById("entry-form");
  if (!root || !form) return;

  const entryType = root.dataset.entryType;
  const planType = entryType === "attendance" ? "Attendance" : "Specials";
  const villageSelect = document.getElementById("village-select");
  const committeeSelect = document.getElementById("committee-select");
  const planSelect = document.getElementById("action-plan-select");
  const entryDate = document.getElementById("entry-date");
  const statusPreview = document.getElementById("status-preview");
  const reasonField = document.getElementById("reason-field");
  const reason = document.getElementById("reason");
  const errorHost = document.getElementById("entry-error");
  const submissionId = document.getElementById("client-submission-id");
  const latitude = document.getElementById("latitude");
  const longitude = document.getElementById("longitude");
  const photoInput = document.getElementById("photo-input");
  const preview = document.getElementById("photo-preview");
  const draftState = document.getElementById("draft-state");
  const submitButton = document.getElementById("submit-entry");
  const specialTitle = document.getElementById("special-title");

  const male = document.getElementById("male-count");
  const female = document.getElementById("female-count");
  const liveTotal = document.getElementById("attendance-total");
  const maleMaster = document.getElementById("male-master");
  const femaleMaster = document.getElementById("female-master");
  const masterTotal = document.getElementById("member-master-total");
  const memberIdsInput = document.getElementById("visit-member-ids");
  const designationGrid = document.getElementById("designation-grid");
  const selectedHost = document.getElementById("selected-visit-members");
  const memberDialog = document.getElementById("member-picker-dialog");
  const memberPickerTitle = document.getElementById("member-picker-title");
  const memberPickerList = document.getElementById("member-picker-list");
  const memberSearch = document.getElementById("member-search");

  const esc = window.MV.escapeHtml;
  const designationOrder = ["President", "Vice President", "Secretary", "Member"];
  let plans = new Map();
  let committeeMembers = [];
  let selectedMembers = new Map();
  let activePickerDesignation = null;
  let pickerDraft = new Set();
  let compressedPhoto = null;

  const freshSubmissionId = () => {
    submissionId.value = crypto.randomUUID();
  };
  freshSubmissionId();

  const localISO = root.dataset.today || new Date().toISOString().slice(0, 10);
  const currentMonth = root.dataset.currentMonth || localISO.slice(0, 7);
  entryDate.value = localISO;

  const showError = (message) => {
    errorHost.textContent = message;
    errorHost.classList.remove("hidden");
  };
  const clearError = () => {
    errorHost.textContent = "";
    errorHost.classList.add("hidden");
  };

  const requestJson = async (url) => {
    const response = await window.MV.api(url);
    let payload = {};
    try { payload = await response.json(); } catch (_) { /* noop */ }
    if (!response.ok) throw new Error(payload.error || `Request failed (${response.status}).`);
    return payload;
  };

  const loadVillages = async () => {
    try {
      const data = await requestJson("/api/v1/villages");
      villageSelect.innerHTML = `<option value="">Select village</option>${data.items.map((v) => `<option value="${v.id}">${esc(v.name)}</option>`).join("")}`;
    } catch (error) {
      showError(error.message);
    }
  };

  const clearCommitteeState = () => {
    committeeSelect.innerHTML = `<option value="">Select committee</option>`;
    committeeSelect.disabled = true;
    planSelect.innerHTML = `<option value="">Select assigned plan</option>`;
    planSelect.disabled = true;
    plans.clear();
    clearMembers();
    updateStatus();
    if (specialTitle) specialTitle.value = "";
    if (maleMaster) maleMaster.textContent = "—";
    if (femaleMaster) femaleMaster.textContent = "—";
    if (masterTotal) masterTotal.textContent = "—";
  };

  villageSelect.addEventListener("change", async () => {
    clearError();
    clearCommitteeState();
    if (!villageSelect.value) return;
    try {
      const data = await requestJson(`/api/v1/villages/${encodeURIComponent(villageSelect.value)}/committees`);
      committeeSelect.innerHTML = `<option value="">Select committee</option>${data.items.map((c) =>
        `<option value="${c.id}" data-male="${c.male_master}" data-female="${c.female_master}" data-total="${c.member_total}">${esc(c.name)}</option>`
      ).join("")}`;
      committeeSelect.disabled = false;
    } catch (error) {
      showError(error.message);
    }
  });

  committeeSelect.addEventListener("change", async () => {
    clearError();
    planSelect.innerHTML = `<option value="">Select assigned plan</option>`;
    planSelect.disabled = true;
    plans.clear();
    clearMembers();

    const option = committeeSelect.selectedOptions[0];
    if (maleMaster) maleMaster.textContent = option?.dataset.male || "—";
    if (femaleMaster) femaleMaster.textContent = option?.dataset.female || "—";
    if (masterTotal) masterTotal.textContent = option?.dataset.total || "—";
    if (specialTitle) specialTitle.value = option?.textContent?.trim() || "";

    if (!committeeSelect.value) return;
    try {
      const [planData, memberData] = await Promise.all([
        requestJson(`/api/v1/committees/${encodeURIComponent(committeeSelect.value)}/action-plans?type=${encodeURIComponent(planType)}&executable=1&pending=1&month=${encodeURIComponent(currentMonth)}`),
        entryType === "attendance"
          ? requestJson(`/api/v1/committees/${encodeURIComponent(committeeSelect.value)}/members`)
          : Promise.resolve({ items: [] }),
      ]);
      plans = new Map((planData.items || []).map((plan) => [String(plan.id), plan]));
      planSelect.innerHTML = `<option value="">Select assigned plan</option>${(planData.items || []).map((plan) =>
        `<option value="${plan.id}">${esc(plan.plan_month?.slice(0, 7) || "")} · due ${esc(plan.assigned_date)} · ${esc(plan.status)}</option>`
      ).join("")}`;
      planSelect.disabled = !planData.items?.length;
      document.getElementById("plan-help").textContent = planData.items?.length
        ? `${planData.items.length} assigned ${planType} plan${planData.items.length === 1 ? "" : "s"} available.`
        : `No assigned ${planType} plan is ready. Ask your PC to complete the monthly Action Plan.`;

      if (entryType === "attendance") {
        committeeMembers = memberData.items || [];
        renderDesignationButtons();
      }
      updateStatus();
    } catch (error) {
      showError(error.message);
    }
  });

  planSelect.addEventListener("change", updateStatus);
  entryDate.addEventListener("change", updateStatus);

  function updateStatus() {
    const plan = plans.get(planSelect.value);
    const dateValue = entryDate.value;
    let status = null;
    if (plan?.assigned_date && dateValue) {
      status = dateValue < plan.assigned_date ? "Early" : dateValue === plan.assigned_date ? "On-time" : "Postponed";
    }
    statusPreview.textContent = status || "Choose plan and date";
    statusPreview.dataset.status = status || "";
    statusPreview.classList.toggle("neutral", !status);
    const needsReason = status === "Early" || status === "Postponed";
    reasonField.classList.toggle("hidden", !needsReason);
    reason.required = needsReason;
    if (!needsReason) reason.value = "";
  }

  function clearMembers() {
    committeeMembers = [];
    selectedMembers.clear();
    activePickerDesignation = null;
    pickerDraft.clear();
    if (memberIdsInput) memberIdsInput.value = "[]";
    if (selectedHost) selectedHost.innerHTML = "";
    designationGrid?.querySelectorAll("[data-designation]").forEach((button) => {
      button.disabled = true;
      button.classList.remove("is-selected");
      button.querySelector("[data-designation-count]").textContent = "Choose committee";
    });
  }

  function groupMembers() {
    const groups = new Map(designationOrder.map((name) => [name, []]));
    committeeMembers.forEach((member) => {
      if (groups.has(member.designation)) groups.get(member.designation).push(member);
    });
    return groups;
  }

  function renderDesignationButtons() {
    const groups = groupMembers();
    designationGrid?.querySelectorAll("[data-designation]").forEach((button) => {
      const name = button.dataset.designation;
      const members = groups.get(name) || [];
      const selectedCount = members.filter((m) => selectedMembers.has(m.id)).length;
      button.disabled = members.length === 0;
      button.classList.toggle("is-selected", selectedCount > 0);
      const small = button.querySelector("[data-designation-count]");
      if (!members.length) small.textContent = "No name in master";
      else if (members.length === 1) small.textContent = selectedCount ? members[0].name : members[0].name;
      else small.textContent = selectedCount ? `${selectedCount} selected · ${members.length} names` : `${members.length} names`;
    });
    renderSelectedMembers();
  }

  function renderSelectedMembers() {
    if (!selectedHost) return;
    const values = [...selectedMembers.values()].sort((a, b) => {
      const di = designationOrder.indexOf(a.designation) - designationOrder.indexOf(b.designation);
      return di || a.name.localeCompare(b.name);
    });
    memberIdsInput.value = JSON.stringify(values.map((m) => m.id));
    if (!values.length) {
      selectedHost.innerHTML = `<span class="muted">No visit designation selected.</span>`;
      return;
    }
    selectedHost.innerHTML = values.map((m) => `<span class="selected-member-pill"><b>${esc(m.designation)}</b>${esc(m.name)}<button type="button" data-remove-member="${m.id}" aria-label="Remove ${esc(m.name)}">×</button></span>`).join("");
  }

  designationGrid?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-designation]");
    if (!button || button.disabled) return;
    const designation = button.dataset.designation;
    const matches = committeeMembers.filter((m) => m.designation === designation);
    if (matches.length === 1) {
      const member = matches[0];
      if (selectedMembers.has(member.id)) selectedMembers.delete(member.id);
      else selectedMembers.set(member.id, member);
      renderDesignationButtons();
      return;
    }
    if (matches.length > 1) openMemberPicker(designation, matches);
  });

  selectedHost?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-remove-member]");
    if (!button) return;
    selectedMembers.delete(Number(button.dataset.removeMember));
    renderDesignationButtons();
  });

  function openMemberPicker(designation, matches) {
    activePickerDesignation = designation;
    pickerDraft = new Set(matches.filter((m) => selectedMembers.has(m.id)).map((m) => m.id));
    memberPickerTitle.textContent = designation;
    memberSearch.value = "";
    renderPicker(matches);
    memberDialog.showModal();
  }

  function renderPicker(source = null) {
    if (!activePickerDesignation) return;
    const matches = source || committeeMembers.filter((m) => m.designation === activePickerDesignation);
    const q = memberSearch.value.trim().toLowerCase();
    const visible = matches.filter((m) => !q || m.name.toLowerCase().includes(q));
    memberPickerList.innerHTML = visible.map((m) => `<label class="member-choice"><input type="checkbox" value="${m.id}" ${pickerDraft.has(m.id) ? "checked" : ""}><span><strong>${esc(m.name)}</strong><small>${esc(m.gender || "Gender not recorded")}</small></span></label>`).join("") || `<div class="empty-state">No names match.</div>`;
  }

  memberSearch?.addEventListener("input", () => renderPicker());
  memberPickerList?.addEventListener("change", (event) => {
    const input = event.target.closest('input[type="checkbox"]');
    if (!input) return;
    const id = Number(input.value);
    if (input.checked) pickerDraft.add(id); else pickerDraft.delete(id);
  });
  document.querySelectorAll("[data-close-member-picker]").forEach((button) => button.addEventListener("click", () => memberDialog?.close()));
  document.getElementById("member-picker-done")?.addEventListener("click", () => {
    const matches = committeeMembers.filter((m) => m.designation === activePickerDesignation);
    matches.forEach((m) => selectedMembers.delete(m.id));
    matches.filter((m) => pickerDraft.has(m.id)).forEach((m) => selectedMembers.set(m.id, m));
    memberDialog.close();
    renderDesignationButtons();
  });

  const updateCounts = () => {
    if (!liveTotal) return;
    liveTotal.textContent = Math.max(0, Number(male.value || 0)) + Math.max(0, Number(female.value || 0));
  };
  male?.addEventListener("input", updateCounts);
  female?.addEventListener("input", updateCounts);

  const captureLocation = () => {
    const label = document.getElementById("location-label");
    const detail = document.getElementById("location-detail");
    if (!navigator.geolocation) {
      label.textContent = "GPS unavailable";
      detail.textContent = "Village master coordinates will be used.";
      return;
    }
    label.textContent = "Finding location…";
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        latitude.value = pos.coords.latitude.toFixed(6);
        longitude.value = pos.coords.longitude.toFixed(6);
        label.textContent = "Current location captured";
        detail.textContent = `${latitude.value}, ${longitude.value} · ±${Math.round(pos.coords.accuracy)} m`;
      },
      () => {
        latitude.value = "";
        longitude.value = "";
        label.textContent = "Using village location fallback";
        detail.textContent = "GPS permission unavailable; master location will be used.";
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
    );
  };
  document.getElementById("retry-location")?.addEventListener("click", captureLocation);
  captureLocation();

  const imageBitmap = async (file) => {
    if ("createImageBitmap" in window) return createImageBitmap(file);
    return new Promise((resolve, reject) => {
      const image = new Image();
      const url = URL.createObjectURL(file);
      image.onload = () => {
        URL.revokeObjectURL(url);
        resolve({
          width: image.naturalWidth,
          height: image.naturalHeight,
          close() {},
          _image: image,
        });
      };
      image.onerror = () => { URL.revokeObjectURL(url); reject(new Error("Could not read this image.")); };
      image.src = url;
    });
  };
  const canvasBlob = (canvas, type, quality) => new Promise((resolve) => canvas.toBlob(resolve, type, quality));

  const compressImage = async (file) => {
    if (!file.type.startsWith("image/")) throw new Error("Choose a valid image.");
    if (file.size > 12 * 1024 * 1024) throw new Error("Choose an image smaller than 12 MB.");
    const image = await imageBitmap(file);
    const maxEdge = 1600;
    const scale = Math.min(1, maxEdge / Math.max(image.width, image.height));
    const width = Math.max(1, Math.round(image.width * scale));
    const height = Math.max(1, Math.round(image.height * scale));
    const canvas = document.createElement("canvas");
    canvas.width = width; canvas.height = height;
    const context = canvas.getContext("2d", { alpha: false });
    context.fillStyle = "#F3F1EA"; context.fillRect(0, 0, width, height);
    context.drawImage(image._image || image, 0, 0, width, height);
    image.close?.();
    const blob = await canvasBlob(canvas, "image/webp", 0.82);
    if (!blob) throw new Error("This browser could not convert the photo to WebP.");
    return new File([blob], `field-${submissionId.value}.webp`, { type: "image/webp", lastModified: Date.now() });
  };

  photoInput.addEventListener("change", async () => {
    clearError();
    const file = photoInput.files?.[0];
    if (!file) return;
    try {
      draftState.textContent = "Converting photo…";
      compressedPhoto = await compressImage(file);
      const image = preview.querySelector("img");
      if (image.dataset.objectUrl) URL.revokeObjectURL(image.dataset.objectUrl);
      const url = URL.createObjectURL(compressedPhoto);
      image.src = url; image.dataset.objectUrl = url;
      preview.classList.remove("hidden");
      draftState.textContent = `${Math.max(1, Math.round(compressedPhoto.size / 1024))} KB WebP ready`;
    } catch (error) {
      compressedPhoto = null; photoInput.value = "";
      showError(error.message); draftState.textContent = "Photo not ready";
    }
  });
  document.getElementById("remove-photo")?.addEventListener("click", () => {
    const image = preview.querySelector("img");
    if (image.dataset.objectUrl) URL.revokeObjectURL(image.dataset.objectUrl);
    image.removeAttribute("src"); delete image.dataset.objectUrl;
    preview.classList.add("hidden"); photoInput.value = ""; compressedPhoto = null;
  });

  const formData = () => {
    const data = new FormData(form);
    data.delete("photo");
    if (compressedPhoto) data.append("photo", compressedPhoto, compressedPhoto.name);
    return data;
  };

  const queue = async (data) => {
    if (!window.MVQueue) throw new Error("Offline queue is unavailable in this browser.");
    await window.MVQueue.enqueue({
      id: submissionId.value,
      userId: window.MV.userId,
      url: entryType === "attendance" ? "/api/v1/attendance" : "/api/v1/specials",
      method: "POST",
      formData: data,
      entryType,
    });
    window.dispatchEvent(new CustomEvent("mv:queue-changed"));
    window.MV.toast("Saved offline. It will sync when connectivity returns.", "success");
    resetAfterSubmit();
  };

  const resetAfterSubmit = () => {
    form.reset();
    freshSubmissionId();
    entryDate.value = localISO;
    clearCommitteeState();
    villageSelect.value = "";
    compressedPhoto = null;
    preview.classList.add("hidden");
    latitude.value = ""; longitude.value = "";
    updateCounts();
    updateStatus();
    captureLocation();
    draftState.textContent = "Ready";
  };

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearError();
    updateStatus();
    if (!form.reportValidity()) return;
    if (!planSelect.value) return showError("Choose an assigned monthly action plan.");
    if (entryType === "attendance" && !selectedMembers.size) {
      return showError("Select at least one Visit designation / Committee Member Name.");
    }

    const data = formData();
    if (!navigator.onLine) {
      try { await queue(data); } catch (error) { showError(error.message); }
      return;
    }

    submitButton.disabled = true;
    draftState.textContent = "Submitting…";
    try {
      const endpoint = entryType === "attendance" ? "/api/v1/attendance" : "/api/v1/specials";
      const response = await window.MV.api(endpoint, { method: "POST", body: data });
      let payload = {};
      try { payload = await response.json(); } catch (_) { /* noop */ }
      if (!response.ok) throw new Error(payload.error || "Submission was rejected.");
      window.MV.toast(payload.idempotent ? "Already submitted" : "Field entry submitted", "success");
      resetAfterSubmit();
    } catch (error) {
      if (!navigator.onLine || error instanceof TypeError) {
        try { await queue(data); } catch (queueError) { showError(queueError.message); }
      } else {
        showError(error.message);
        draftState.textContent = "Fix the highlighted issue";
      }
    } finally {
      submitButton.disabled = false;
    }
  });

  loadVillages();
})();
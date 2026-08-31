(() => {
  "use strict";

  const root = document.querySelector(".planning-page");
  if (!root) return;

  const esc = window.MV.escapeHtml;
  const isDaWorkHub = root.dataset.daWorkHub === "1";

  const serverEpoch = Date.parse(
    root.dataset.serverNow || new Date().toISOString()
  );
  const pageLoadedAt = Date.now();
  const appTimeZone = root.dataset.appTimezone || "Asia/Kolkata";

  const updateToday = () => {
    const node = document.querySelector("[data-today-stamp]");
    if (!node) return;

    const now = new Date(
      serverEpoch + (Date.now() - pageLoadedAt)
    );

    node.innerHTML = `
      <strong>${
        new Intl.DateTimeFormat(undefined, {
          weekday: "long",
          timeZone: appTimeZone,
        }).format(now)
      }</strong>
      <span>${
        new Intl.DateTimeFormat(undefined, {
          dateStyle: "long",
          timeZone: appTimeZone,
        }).format(now)
      }</span>
      <small>${
        new Intl.DateTimeFormat(undefined, {
          timeStyle: "short",
          timeZone: appTimeZone,
        }).format(now)
      }</small>
    `;
  };

  updateToday();
  window.setInterval(updateToday, 60000);

  /*
   * ------------------------------------------------------------------
   * DA FIELD-WORK HUB
   * ------------------------------------------------------------------
   */

  function drawAttentionToFirstDaAction() {
  const firstAction =
    document.querySelector(
      '[data-work-panel="today"] .da-work-go'
    ) ||
    document.querySelector(
      '[data-work-panel="pending"] .da-work-go'
    );

    if (!firstAction) {
      return;
    }

    const reduceMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    );

    if (reduceMotion.matches) {
      return;
    }

    if (firstAction.dataset.attentionShown === "1") {
      return;
    }

    firstAction.dataset.attentionShown = "1";
    firstAction.classList.add(
      "is-attention-pulse"
    );

    firstAction.addEventListener(
      "animationend",
      () => {
        firstAction.classList.remove(
          "is-attention-pulse"
        );
      },
      {
        once: true,
      }
    );
  }


  const initDaWorkHub = () => {
    const todayList = document.querySelector("[data-today-work]");
    const pendingList = document.querySelector("[data-pending-work]");
    const upcomingList = document.querySelector("[data-upcoming-list]");

    const todayTab = document.querySelector(
      '[data-work-tab="today"]'
    );
    const pendingTab = document.querySelector(
      '[data-work-tab="pending"]'
    );

    const todayPanel = document.querySelector(
      '[data-work-panel="today"]'
    );
    const pendingPanel = document.querySelector(
      '[data-work-panel="pending"]'
    );

    if (
      !todayList ||
      !pendingList ||
      !upcomingList ||
      !todayTab ||
      !pendingTab ||
      !todayPanel ||
      !pendingPanel
    ) {
      return;
    }

    const counts = {
      today: document.querySelector(
        '[data-work-count="today"]'
      ),
      pending: document.querySelector(
        '[data-work-count="pending"]'
      ),
      upcoming: document.querySelector(
        '[data-work-count="upcoming"]'
      ),
    };

    const formatDate = (value) => {
      if (!value) return "Date not assigned";

      const date = new Date(`${value}T00:00:00`);

      if (Number.isNaN(date.getTime())) {
        return value;
      }

      return new Intl.DateTimeFormat(undefined, {
        day: "numeric",
        month: "short",
        year: "numeric",
        timeZone: appTimeZone,
      }).format(date);
    };

    const typeClass = (type) => {
      return type === "Specials"
        ? "specials"
        : "attendance";
    };

    const emptyState = (title, message) => `
      <div class="empty-state da-work-empty">
        <strong>${esc(title)}</strong>
        <span>${esc(message)}</span>
      </div>
    `;

    const goButton = (item) => {
      if (!item.go_url) return "";

      return `
        <a
          class="button primary da-work-go"
          href="${esc(item.go_url)}"
          aria-label="Start ${esc(item.plan_type)} work for ${esc(
            item.village_name
          )}, ${esc(item.committee_name)}"
        >GO</a>
      `;
    };

    const workCard = (item, bucket) => {
      const pending = bucket === "pending";
      const upcoming = bucket === "upcoming";

      let timing = "";

      if (bucket === "today") {
        timing = `
          <span class="da-work-timing due-today">
            Due today
          </span>
        `;
      } else if (pending) {
        const days = Number(item.days_overdue || 0);

        timing = `
          <span class="da-work-timing overdue">
            Due ${esc(formatDate(item.assigned_date))}
            ${
              days > 0
                ? ` · ${days} day${days === 1 ? "" : "s"} overdue`
                : ""
            }
          </span>
        `;
      } else {
        timing = `
          <span class="da-work-timing upcoming">
            Scheduled ${esc(formatDate(item.assigned_date))}
          </span>
        `;
      }

      return `
        <article
          class="da-work-card"
          data-plan-id="${esc(String(item.plan_id))}"
          data-plan-type="${esc(item.plan_type)}"
        >
          <div class="da-work-card-main">
            <div class="da-work-location">
              <strong>${esc(item.village_name)}</strong>
              <span>${esc(item.committee_name)}</span>
            </div>

            <div class="da-work-meta">
              <span
                class="badge da-work-type"
                data-plan-type="${esc(typeClass(item.plan_type))}"
              >
                ${esc(item.plan_type)}
              </span>

              ${timing}
            </div>

            ${
              item.notes
                ? `
                  <p class="da-work-notes">
                    ${esc(item.notes)}
                  </p>
                `
                : ""
            }
          </div>

          ${
            upcoming
              ? `
                <span
                  class="da-work-upcoming-label"
                  aria-label="This assignment is not due yet"
                >
                  Upcoming
                </span>
              `
              : goButton(item)
          }
        </article>
      `;
    };

    const renderBucket = (
      node,
      items,
      bucket,
      emptyTitle,
      emptyMessage
    ) => {
      if (!items.length) {
        node.innerHTML = emptyState(
          emptyTitle,
          emptyMessage
        );
        return;
      }

      node.innerHTML = items
        .map((item) => workCard(item, bucket))
        .join("");
    };

    const activateTab = (name, focus = false) => {
      const showToday = name === "today";

      todayTab.classList.toggle(
        "is-active",
        showToday
      );
      pendingTab.classList.toggle(
        "is-active",
        !showToday
      );

      todayTab.setAttribute(
        "aria-selected",
        showToday ? "true" : "false"
      );
      pendingTab.setAttribute(
        "aria-selected",
        showToday ? "false" : "true"
      );

      todayTab.tabIndex = showToday ? 0 : -1;
      pendingTab.tabIndex = showToday ? -1 : 0;

      todayPanel.hidden = !showToday;
      pendingPanel.hidden = showToday;

      todayPanel.classList.toggle(
        "hidden",
        !showToday
      );
      pendingPanel.classList.toggle(
        "hidden",
        showToday
      );

      if (focus) {
        (
          showToday
            ? todayTab
            : pendingTab
        ).focus();
      }
    };

    todayTab.addEventListener("click", () => {
      activateTab("today");
    });

    pendingTab.addEventListener("click", () => {
      activateTab("pending");
    });

    todayTab.addEventListener("keydown", (event) => {
      if (
        event.key !== "ArrowRight" &&
        event.key !== "ArrowLeft"
      ) {
        return;
      }

      event.preventDefault();
      activateTab("pending", true);
    });

    pendingTab.addEventListener("keydown", (event) => {
      if (
        event.key !== "ArrowRight" &&
        event.key !== "ArrowLeft"
      ) {
        return;
      }

      event.preventDefault();
      activateTab("today", true);
    });

    /*
     * Swipe support.
     *
     * Swipe left  : Today -> Pending
     * Swipe right : Pending -> Today
     *
     * Normal tab buttons remain available for accessibility.
     */
    let touchStartX = null;
    let touchStartY = null;

    const swipeArea = document.querySelector(
      ".work-tab-panels"
    );

    swipeArea?.addEventListener(
      "touchstart",
      (event) => {
        const touch = event.changedTouches?.[0];

        if (!touch) return;

        touchStartX = touch.clientX;
        touchStartY = touch.clientY;
      },
      {
        passive: true,
      }
    );

    swipeArea?.addEventListener(
      "touchend",
      (event) => {
        if (
          touchStartX === null ||
          touchStartY === null
        ) {
          return;
        }

        const touch = event.changedTouches?.[0];

        if (!touch) {
          touchStartX = null;
          touchStartY = null;
          return;
        }

        const deltaX =
          touch.clientX - touchStartX;
        const deltaY =
          touch.clientY - touchStartY;

        touchStartX = null;
        touchStartY = null;

        /*
         * Ignore vertical scrolling and small accidental movement.
         */
        if (
          Math.abs(deltaX) < 50 ||
          Math.abs(deltaX) <= Math.abs(deltaY)
        ) {
          return;
        }

        if (deltaX < 0) {
          activateTab("pending");
        } else {
          activateTab("today");
        }
      },
      {
        passive: true,
      }
    );

    const setLoading = () => {
      todayList.innerHTML = `
        <div class="skeleton-card">
          Loading today's assignments…
        </div>
      `;

      pendingList.innerHTML = `
        <div class="skeleton-card">
          Loading pending assignments…
        </div>
      `;

      upcomingList.innerHTML = `
        <div class="skeleton-card">
          Loading upcoming assignments…
        </div>
      `;
    };

    const showLoadFailure = (message) => {
      const alert = `
        <div class="form-alert" role="alert">
          ${esc(message)}
        </div>
      `;

      todayList.innerHTML = alert;
      pendingList.innerHTML = alert;
      upcomingList.innerHTML = alert;
    };

    const loadDaWork = async () => {
      setLoading();

      try {
        const response = await window.MV.api(
          "/api/v1/planning/da-work"
        );

        const payload = await response.json();

        if (!response.ok) {
          throw new Error(
            payload.error ||
              "Could not load your action plans."
          );
        }

        const today = Array.isArray(payload.today)
          ? payload.today
          : [];

        const pending = Array.isArray(payload.pending)
          ? payload.pending
          : [];

        const upcoming = Array.isArray(payload.upcoming)
          ? payload.upcoming
          : [];

        const payloadCounts = payload.counts || {};

        if (counts.today) {
          counts.today.textContent = String(
            payloadCounts.today ?? today.length
          );
        }

        if (counts.pending) {
          counts.pending.textContent = String(
            payloadCounts.pending ?? pending.length
          );
        }

        if (counts.upcoming) {
          counts.upcoming.textContent = String(
            payloadCounts.upcoming ?? upcoming.length
          );
        }

        renderBucket(
          todayList,
          today,
          "today",
          "You're all caught up.",
          "No assignments are due today."
        );

        renderBucket(
          pendingList,
          pending,
          "pending",
          "Nothing pending.",
          "You have no overdue field assignments."
        );

        renderBucket(
          upcomingList,
          upcoming,
          "upcoming",
          "Nothing upcoming.",
          "No more assignments are scheduled this month."
        );

        /*
         * If there is no work today but overdue work exists,
         * take the DA directly to Pending.
         */
        if (
          today.length === 0 &&
          pending.length > 0
        ) {
          activateTab("pending");
        } else {
          activateTab("today");
        }
      } catch (error) {
        showLoadFailure(
          error.message ||
            "Could not load your action plans."
        );
      }
    };

    activateTab("today");
    loadDaWork();
  };

  if (isDaWorkHub) {
    initDaWorkHub();
    return;
  }

  /*
   * ------------------------------------------------------------------
   * ADMIN / PM / PC MONTHLY PLANNING WORKSPACE
   * ------------------------------------------------------------------
   */

  const monthInput = document.getElementById(
    "planning-month"
  );
  const label = document.getElementById(
    "month-label"
  );
  const list = document.getElementById(
    "plan-list"
  );
  const search = document.getElementById(
    "plan-search"
  );
  const statusFilter = document.getElementById(
    "plan-status-filter"
  );
  const transferLink = document.querySelector(
    "[data-transfer-link]"
  );

  if (
    !monthInput ||
    !label ||
    !list
  ) {
    return;
  }

  const canManage =
    root.dataset.canManage === "1";

  const dialog = document.getElementById(
    "plan-edit-dialog"
  );
  const form = document.getElementById(
    "plan-edit-form"
  );

  let rows = [];

  const monthDate = (value) =>
    new Date(
      `${value}-01T00:00:00`
    );

  const monthValue = (date) =>
    `${date.getFullYear()}-${String(
      date.getMonth() + 1
    ).padStart(2, "0")}`;

  const currentMonth =
    root.dataset.currentMonth ||
    monthInput.value;

  const badge = (status) => `
    <span
      class="badge"
      data-status="${esc(status)}"
    >${esc(status)}</span>
  `;

  const renderMetrics = (summary) => {
    Object.entries(summary || {}).forEach(
      ([key, value]) => {
        document
          .querySelector(
            `[data-metric="${key}"]`
          )
          ?.replaceChildren(
            document.createTextNode(
              value
            )
          );
      }
    );
  };

  const filtered = () => {
    const q = (
      search?.value || ""
    )
      .trim()
      .toLowerCase();

    const status =
      statusFilter?.value || "";

    return rows.filter((row) => {
      const hay = `
        ${row.da_name}
        ${row.village_name}
        ${row.committee_name}
        ${row.plan_type || ""}
      `.toLowerCase();

      return (
        (!q || hay.includes(q)) &&
        (!status ||
          row.status === status)
      );
    });
  };

  const render = () => {
    const data = filtered();

    if (!data.length) {
      list.innerHTML = `
        <div class="empty-state">
          <strong>
            No action plans match.
          </strong>
          <span>
            Change the filters or planning month.
          </span>
        </div>
      `;
      return;
    }

    list.innerHTML = `
      <div
        class="ledger-table-wrap desktop-ledger"
      >
        <table
          class="ledger modern-ledger"
        >
          <thead>
            <tr>
              <th>DA</th>
              <th>Village</th>
              <th>Committee</th>
              <th>Type</th>
              <th>Assigned</th>
              <th>Status</th>
              ${
                canManage
                  ? "<th></th>"
                  : ""
              }
            </tr>
          </thead>

          <tbody>
            ${data
              .map(
                (row) => `
                  <tr>
                    <td>
                      ${esc(row.da_name)}
                    </td>
                    <td>
                      ${esc(row.village_name)}
                    </td>
                    <td>
                      ${esc(row.committee_name)}
                    </td>
                    <td>
                      ${esc(
                        row.plan_type ||
                          "Draft"
                      )}
                    </td>
                    <td>
                      ${esc(
                        row.assigned_date ||
                          "—"
                      )}
                    </td>
                    <td>
                      ${badge(row.status)}
                    </td>

                    ${
                      canManage
                        ? `
                          <td>
                            ${
                              row.locked
                                ? `
                                  <span
                                    class="mono muted"
                                  >
                                    Locked
                                  </span>
                                `
                                : `
                                  <button
                                    class="text-button"
                                    type="button"
                                    data-edit-plan="${
                                      row.plan_id ||
                                      ""
                                    }"
                                    data-committee-id="${
                                      row.committee_id
                                    }"
                                  >
                                    Edit
                                  </button>
                                `
                            }
                          </td>
                        `
                        : ""
                    }
                  </tr>
                `
              )
              .join("")}
          </tbody>
        </table>
      </div>

      <div class="mobile-ledger">
        ${data
          .map(
            (row) => `
              <article
                class="ledger-card"
              >
                <div
                  class="ledger-card-top"
                >
                  <div>
                    <strong>
                      ${esc(
                        row.committee_name
                      )}
                    </strong>

                    <small>
                      ${esc(
                        row.village_name
                      )}
                      ·
                      ${esc(
                        row.da_name
                      )}
                    </small>
                  </div>

                  ${badge(row.status)}
                </div>

                <div
                  class="ledger-card-meta"
                >
                  <span>
                    ${esc(
                      row.plan_type ||
                        "Draft"
                    )}
                  </span>

                  <span>
                    ${esc(
                      row.assigned_date ||
                        "Not assigned"
                    )}
                  </span>
                </div>

                ${
                  canManage
                    ? row.locked
                      ? `
                        <span
                          class="mono muted"
                        >
                          Immutable history
                        </span>
                      `
                      : `
                        <button
                          class="button ghost wide"
                          type="button"
                          data-edit-plan="${
                            row.plan_id || ""
                          }"
                          data-committee-id="${
                            row.committee_id
                          }"
                        >
                          Edit plan
                        </button>
                      `
                    : ""
                }
              </article>
            `
          )
          .join("")}
      </div>
    `;
  };

  const load = async () => {
    list.innerHTML = `
      <div class="skeleton-card">
        Loading action plans…
      </div>
    `;

    const response =
      await window.MV.api(
        `/api/v1/planning/month?month=${encodeURIComponent(
          monthInput.value
        )}`
      );

    const payload =
      await response.json();

    if (!response.ok) {
      list.innerHTML = `
        <div class="form-alert">
          ${esc(
            payload.error ||
              "Could not load action plans."
          )}
        </div>
      `;
      return;
    }

    rows = payload.rows || [];

    label.textContent =
      payload.label;

    renderMetrics(
      payload.summary
    );

    if (transferLink) {
      transferLink.href =
        `/action-plans/transfer?month=${encodeURIComponent(
          monthInput.value
        )}`;
    }

    const url = new URL(
      window.location.href
    );

    url.searchParams.set(
      "month",
      monthInput.value
    );

    history.replaceState(
      {},
      "",
      url
    );

    render();
  };

  const stepMonth = (delta) => {
    const date = monthDate(
      monthInput.value
    );

    date.setMonth(
      date.getMonth() + delta
    );

    monthInput.value =
      monthValue(date);

    load();
  };

  document
    .querySelectorAll(
      "[data-month-step]"
    )
    .forEach((button) =>
      button.addEventListener(
        "click",
        () =>
          stepMonth(
            Number(
              button.dataset.monthStep
            )
          )
      )
    );

  document
    .querySelector(
      "[data-current-month]"
    )
    ?.addEventListener(
      "click",
      () => {
        monthInput.value =
          currentMonth;

        load();
      }
    );

  monthInput.addEventListener(
    "change",
    load
  );

  search?.addEventListener(
    "input",
    render
  );

  statusFilter?.addEventListener(
    "change",
    render
  );

  const rowByPlan = (
    planId,
    committeeId
  ) =>
    rows.find(
      (row) =>
        (
          planId &&
          String(row.plan_id) ===
            String(planId)
        ) ||
        (
          !planId &&
          String(
            row.committee_id
          ) ===
            String(
              committeeId
            )
        )
    );

  list.addEventListener(
    "click",
    (event) => {
      const button =
        event.target.closest(
          "[data-edit-plan]"
        );

      if (
        !button ||
        !canManage ||
        !dialog ||
        !form
      ) {
        return;
      }

      const row = rowByPlan(
        button.dataset.editPlan,
        button.dataset.committeeId
      );

      if (!row) return;

      document.getElementById(
        "plan-edit-id"
      ).value =
        row.plan_id || "";

      form.dataset.committeeId =
        row.committee_id;

      document.getElementById(
        "plan-edit-title"
      ).textContent =
        `${row.village_name} · ${row.committee_name}`;

      document.getElementById(
        "plan-edit-type"
      ).value =
        row.plan_type || "";

      document.getElementById(
        "plan-edit-date"
      ).value =
        row.assigned_date || "";

      document.getElementById(
        "plan-edit-notes"
      ).value =
        row.notes || "";

      document
        .getElementById(
          "plan-edit-error"
        )
        .classList.add(
          "hidden"
        );

      dialog.showModal();
    }
  );

  document
    .querySelectorAll(
      "[data-close-plan]"
    )
    .forEach((button) =>
      button.addEventListener(
        "click",
        () => dialog?.close()
      )
    );

  form?.addEventListener(
    "submit",
    async (event) => {
      event.preventDefault();

      const error =
        document.getElementById(
          "plan-edit-error"
        );

      error.classList.add(
        "hidden"
      );

      const planId =
        document.getElementById(
          "plan-edit-id"
        ).value;

      const payload = {
        month:
          monthInput.value,

        committee_id: Number(
          form.dataset.committeeId
        ),

        plan_type:
          document.getElementById(
            "plan-edit-type"
          ).value,

        assigned_date:
          document.getElementById(
            "plan-edit-date"
          ).value,

        notes:
          document.getElementById(
            "plan-edit-notes"
          ).value,
      };

      const url = planId
        ? `/api/v1/planning/plans/${planId}`
        : "/api/v1/planning/plans";

      const response =
        await window.MV.api(
          url,
          {
            method: planId
              ? "PATCH"
              : "POST",
            headers: {
              "Content-Type":
                "application/json",
            },
            body: JSON.stringify(
              payload
            ),
          }
        );

      const result =
        await response.json();

      if (!response.ok) {
        error.textContent =
          result.error ||
          "Could not save the plan.";

        error.classList.remove(
          "hidden"
        );

        return;
      }

      dialog.close();

      window.MV.toast(
        "Action plan saved",
        "success"
      );

      load();
    }
  );

  document
    .getElementById(
      "prepare-next-month"
    )
    ?.addEventListener(
      "click",
      async (event) => {
        const button =
          event.currentTarget;

        if (
          !confirm(
            `Prepare the month after ${label.textContent}? Dates are intentionally not copied.`
          )
        ) {
          return;
        }

        button.disabled = true;

        try {
          const response =
            await window.MV.api(
              "/api/v1/planning/prepare-next-month",
              {
                method: "POST",
                headers: {
                  "Content-Type":
                    "application/json",
                },
                body: JSON.stringify(
                  {
                    month:
                      monthInput.value,
                  }
                ),
              }
            );

          const result =
            await response.json();

          if (!response.ok) {
            throw new Error(
              result.error ||
                "Could not prepare next month."
            );
          }

          window.MV.toast(
            `Prepared ${result.created} plans for ${result.target_month}`,
            "success"
          );

          monthInput.value =
            result.target_month;

          load();
        } catch (error) {
          window.MV.toast(
            error.message,
            "error"
          );
        } finally {
          button.disabled = false;
        }
      }
    );

  load();
})();
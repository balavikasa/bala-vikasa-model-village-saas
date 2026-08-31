(() => {
  "use strict";

  const body = document.body;

  if (body.dataset.role !== "da") {
    return;
  }

  const entryTrigger = document.querySelector(
    "[data-da-entry-menu]"
  );

  const entryDialog = document.getElementById(
    "da-entry-menu"
  );

  const entryClose = document.querySelector(
    "[data-da-entry-close]"
  );

  if (!entryTrigger || !entryDialog) {
    return;
  }

  const openEntryDialog = () => {
    if (entryDialog.open) {
      return;
    }

    entryTrigger.setAttribute(
      "aria-expanded",
      "true"
    );

    entryDialog.showModal();
  };

  const closeEntryDialog = () => {
    if (!entryDialog.open) {
      return;
    }

    entryDialog.close();

    entryTrigger.setAttribute(
      "aria-expanded",
      "false"
    );
  };

  entryTrigger.addEventListener(
    "click",
    openEntryDialog
  );

  entryClose?.addEventListener(
    "click",
    closeEntryDialog
  );

  entryDialog.addEventListener(
    "cancel",
    () => {
      entryTrigger.setAttribute(
        "aria-expanded",
        "false"
      );
    }
  );

  entryDialog.addEventListener(
    "click",
    (event) => {
      if (event.target === entryDialog) {
        closeEntryDialog();
      }
    }
  );

  entryDialog
    .querySelectorAll("a")
    .forEach((link) => {
      link.addEventListener(
        "click",
        () => {
          entryTrigger.setAttribute(
            "aria-expanded",
            "false"
          );
        }
      );
    });

  const desktopQuery = window.matchMedia(
    "(min-width: 761px)"
  );

  const handleDesktopChange = (
    event
  ) => {
    if (
      event.matches &&
      entryDialog.open
    ) {
      closeEntryDialog();
    }
  };

  desktopQuery.addEventListener?.(
    "change",
    handleDesktopChange
  );
})();
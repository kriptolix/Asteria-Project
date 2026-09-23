(function () {
  "use strict";

  // ---------------------------------------------------------------------
  // Generic tabs component, following the WAI-ARIA Tabs pattern
  // (https://www.w3.org/WAI/ARIA/apg/patterns/tabs/) with automatic
  // activation: moving focus with the arrow keys also switches the
  // active panel.
  //
  // Any number of independent tab groups can live on the same page —
  // just wrap each one in an element with the `data-tabs` attribute.
  // ids on the tab/panel pairs are optional: any pair missing
  // aria-controls/id gets one generated automatically, so hand-written
  // markup can stay minimal and multiple groups never collide.
  //
  // Optional per-group attributes (read from the `data-tabs` element):
  //   data-sync-hash                keep the active tab's panel id in
  //                                  the URL hash (via history.replaceState,
  //                                  so it doesn't add browser history
  //                                  entries or trigger a scroll jump),
  //                                  and restore it from the hash on load.
  //
  // Optional attribute on the [role="tablist"] element:
  //   aria-orientation="vertical"    switches Left/Right to Up/Down for
  //                                  keyboard navigation. Pair with the
  //                                  .tabs--vertical class for the
  //                                  matching layout in tabs.css.
  //
  // No-JS fallback: panels are expected to start without a `hidden`
  // attribute in the markup, so their content stays visible (stacked)
  // if this script fails to load. This script is what hides every
  // panel but the active one.
  // ---------------------------------------------------------------------

  function initTabs(root, groupIndex) {
    var tablist = root.querySelector('[role="tablist"]');
    if (!tablist) return;

    var tabs = Array.prototype.slice.call(tablist.querySelectorAll('[role="tab"]'));
    if (!tabs.length) return;

    var panels = tabs.map(function (tab) {
      var id = tab.getAttribute("aria-controls");
      return id ? document.getElementById(id) : null;
    });

    // Fill in ids/aria-controls/aria-labelledby for any tab/panel pair
    // the author left unlinked.
    tabs.forEach(function (tab, i) {
      var panel = panels[i];
      if (!panel) return;

      if (!tab.id) tab.id = "tabs-" + groupIndex + "-tab-" + i;
      if (!panel.id) panel.id = "tabs-" + groupIndex + "-panel-" + i;

      tab.setAttribute("aria-controls", panel.id);
      panel.setAttribute("aria-labelledby", tab.id);
      panel.setAttribute("role", "tabpanel");
      if (!panel.hasAttribute("tabindex")) panel.tabIndex = 0;
    });

    var orientation =
      tablist.getAttribute("aria-orientation") === "vertical" ? "vertical" : "horizontal";
    var syncHash = root.hasAttribute("data-sync-hash");

    function activate(activeIndex, options) {
      options = options || {};

      tabs.forEach(function (tab, i) {
        var panel = panels[i];
        var isActive = i === activeIndex;

        tab.setAttribute("aria-selected", String(isActive));
        tab.tabIndex = isActive ? 0 : -1;
        if (panel) panel.hidden = !isActive;
      });

      if (options.focus) tabs[activeIndex].focus();

      if (syncHash && panels[activeIndex] && window.history && history.replaceState) {
        history.replaceState(null, "", "#" + panels[activeIndex].id);
      }
    }

    function indexFromHash() {
      if (!location.hash) return -1;
      var id = location.hash.slice(1);
      for (var i = 0; i < panels.length; i++) {
        if (panels[i] && panels[i].id === id) return i;
      }
      return -1;
    }

    tabs.forEach(function (tab, i) {
      tab.addEventListener("click", function () {
        activate(i);
      });
    });

    tablist.addEventListener("keydown", function (event) {
      var currentIndex = tabs.indexOf(document.activeElement);
      if (currentIndex === -1) return;

      var nextKey = orientation === "vertical" ? "ArrowDown" : "ArrowRight";
      var prevKey = orientation === "vertical" ? "ArrowUp" : "ArrowLeft";
      var targetIndex = null;

      if (event.key === nextKey) {
        targetIndex = (currentIndex + 1) % tabs.length;
      } else if (event.key === prevKey) {
        targetIndex = (currentIndex - 1 + tabs.length) % tabs.length;
      } else if (event.key === "Home") {
        targetIndex = 0;
      } else if (event.key === "End") {
        targetIndex = tabs.length - 1;
      }

      if (targetIndex !== null) {
        event.preventDefault();
        activate(targetIndex, { focus: true });
      }
    });

    var initialIndex = syncHash ? indexFromHash() : -1;

    if (initialIndex === -1) {
      initialIndex = tabs.findIndex(function (tab) {
        return tab.getAttribute("aria-selected") === "true";
      });
    }

    if (initialIndex === -1) initialIndex = 0;

    activate(initialIndex);
  }

  document.addEventListener("DOMContentLoaded", function () {
    var groups = document.querySelectorAll("[data-tabs]");
    groups.forEach(function (root, index) {
      initTabs(root, index);
    });
  });
})();

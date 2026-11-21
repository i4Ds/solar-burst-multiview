(function () {
  const q = document.getElementById("q");
  const chips = [...document.querySelectorAll(".chip")];
  let year = "all";
  let calOnly = false;
  let workOnly = false;

  function apply() {
    const needle = (q.value || "").trim().toLowerCase();
    document.querySelectorAll("table.days tbody tr").forEach((tr) => {
      const y = tr.getAttribute("data-year");
      const cal = tr.getAttribute("data-cal") === "1";
      const work = tr.getAttribute("data-work") === "1";
      const text = tr.getAttribute("data-text") || "";
      let ok = year === "all" || y === year;
      if (calOnly && !cal) ok = false;
      if (workOnly && !work) ok = false;
      if (needle && !text.includes(needle)) ok = false;
      tr.classList.toggle("hidden", !ok);
    });
    document.querySelectorAll(".year-head, table.days").forEach((el) => {
      const y = el.getAttribute("data-year");
      const table = document.querySelector("table.days[data-year='" + y + "']");
      const any = table && [...table.querySelectorAll("tbody tr")].some((tr) => !tr.classList.contains("hidden"));
      const showYear = (year === "all" || y === year) && any;
      el.classList.toggle("hidden", !showYear);
    });
  }

  chips.forEach((btn) => {
    btn.addEventListener("click", () => {
      if (btn.dataset.year) {
        year = btn.dataset.year;
        chips.filter((c) => c.dataset.year).forEach((c) =>
          c.setAttribute("aria-pressed", c === btn ? "true" : "false"));
      } else if (btn.dataset.filter === "cal") {
        calOnly = !calOnly;
        btn.setAttribute("aria-pressed", calOnly ? "true" : "false");
      } else if (btn.dataset.filter === "work") {
        workOnly = !workOnly;
        btn.setAttribute("aria-pressed", workOnly ? "true" : "false");
      }
      apply();
    });
  });
  q.addEventListener("input", apply);
})();

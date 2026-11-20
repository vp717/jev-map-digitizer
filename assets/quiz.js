/* Reusable quiz component.
   Markup: <div class="quiz"> <div class="q" data-answer="2"> <p>Question</p>
             <ol class="opts"><li>..</li>...</ol> <p class="why">Explanation</p> </div> ... </div>
   data-answer is the 0-based index of the correct option. */
(function () {
  const css = `
  .quiz .q { margin: 1.4rem 0; padding: 1rem 1.2rem; border: 1px solid var(--rule); border-radius: 8px; }
  .quiz .q > p:first-child { margin-top: 0; font-weight: 600; font-family: var(--sans); font-size: 0.98rem; }
  .quiz .opts { list-style: none; padding: 0; margin: 0.6rem 0; display: grid; gap: 0.45rem; }
  .quiz button { width: 100%; text-align: left; font: inherit; font-size: 0.95rem; color: var(--fg);
    background: var(--bg); border: 1px solid var(--rule); border-radius: 6px; padding: 0.55rem 0.8rem; cursor: pointer; }
  .quiz button:hover:not(:disabled) { border-color: var(--accent); }
  .quiz button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .quiz button.right { background: var(--good-bg); border-color: var(--good); }
  .quiz button.wrong { background: var(--bad-bg); border-color: var(--bad); }
  .quiz .why { display: none; font-size: 0.92rem; color: var(--muted); margin-bottom: 0; }
  .quiz .q.done .why { display: block; }
  .quiz .score { font: 600 0.95rem var(--sans); }`;
  const st = document.createElement("style"); st.textContent = css; document.head.appendChild(st);
  document.querySelectorAll(".quiz").forEach(quiz => {
    const qs = [...quiz.querySelectorAll(".q")];
    let answered = 0, right = 0;
    const score = document.createElement("p"); score.className = "score"; score.setAttribute("aria-live", "polite");
    score.textContent = `0 of ${qs.length} answered`; quiz.appendChild(score);
    qs.forEach(q => {
      const ans = +q.dataset.answer;
      [...q.querySelectorAll(".opts li")].forEach((li, i) => {
        const b = document.createElement("button"); b.type = "button"; b.innerHTML = li.innerHTML;
        li.innerHTML = ""; li.appendChild(b);
        b.addEventListener("click", () => {
          if (q.classList.contains("done")) return;
          q.classList.add("done"); answered++;
          const btns = q.querySelectorAll("button");
          btns[ans].classList.add("right");
          if (i === ans) right++; else b.classList.add("wrong");
          btns.forEach(x => x.disabled = true);
          score.textContent = answered < qs.length ? `${answered} of ${qs.length} answered` :
            `${right} of ${qs.length} correct. ${right === qs.length ? "Solid." : "Reread the matching section, then try the reflection below."}`;
        });
      });
    });
  });
})();

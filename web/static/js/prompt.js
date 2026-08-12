/**
 * The question that turns over in the banner.
 *
 * Its own module rather than a corner of `home.js`, which is about the form —
 * and because the part worth testing is separable from the part that cannot be:
 * `next` is arithmetic, and the tests take it on with no clock and no DOM.
 *
 * **The questions are stacked, not swapped.** All of them sit in one grid cell,
 * so the cell takes the height of the longest and nothing below it moves when
 * one gives way to the next. Replacing the text of a single node instead would
 * make the subtitle and the whole form jump on every turn, by a line or two,
 * every five seconds.
 *
 * **Only the visible one is a heading.** The others carry `aria-hidden`, or the
 * accessible name of the `<h1>` would be all of them read end to end. And the
 * banner is deliberately *not* a live region: a mutation is announced only when
 * asked for, and a title that announced itself every five seconds would be
 * unusable.
 *
 * **It stops when it should.** Under `prefers-reduced-motion`, on hover, on
 * keyboard focus, and when the tab goes to the background. The first three are
 * WCAG 2.2.2 — anything that moves on its own for more than five seconds owes
 * the reader a way to stop it — and the last one is just not burning a timer
 * nobody is looking at.
 */

import { el } from "./dom.js";

export const INTERVAL = 5000;

/**
 * Which question comes after ``index``, wrapping round.
 *
 * Total zero returns zero rather than dividing by it: an empty list is a
 * dictionary that has lost its questions, which must leave the banner empty
 * rather than take the page down.
 */
export function next(index, total) {
  return total > 0 ? (index + 1) % total : 0;
}

/** One stacked span per question, in order. */
export function build(questions) {
  return questions.map((text) => el("span", { className: "prompt-item", text }));
}

/** Show ``index``, hide the rest — from the reader's eye and from the tree alike. */
export function reveal(nodes, index) {
  nodes.forEach((node, position) => {
    const current = position === index;
    node.classList.toggle("is-current", current);
    if (current) node.removeAttribute("aria-hidden");
    else node.setAttribute("aria-hidden", "true");
  });
}

/**
 * Fill ``host`` with the stacked questions and turn them over.
 *
 * The wiring, and the one part of this file the tests leave alone: timers,
 * pointer events and a media query are the browser's, not arithmetic. What is
 * decidable — which node exists, which one is exposed, which comes next — lives
 * in ``build``, ``reveal`` and ``next``, and is tested there.
 *
 * Returns a function that stops the rotation.
 */
export function rotate(host, questions, { interval = INTERVAL } = {}) {
  const nodes = build(questions);
  host.replaceChildren(...nodes);
  if (!nodes.length) return () => {};

  let index = 0;
  reveal(nodes, index);

  // Honoured once, at start-up: a reader who asks for less motion gets the
  // first question and no movement at all, rather than a slower carousel.
  // `globalThis` rather than `window` — the same object in a browser, and one
  // that exists everywhere else.
  const still = globalThis.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  if (still || nodes.length === 1) return () => {};

  let timer = null;
  const stop = () => {
    clearInterval(timer);
    timer = null;
  };
  const start = () => {
    if (timer === null) {
      timer = setInterval(() => {
        index = next(index, nodes.length);
        reveal(nodes, index);
      }, interval);
    }
  };

  host.addEventListener("mouseenter", stop);
  host.addEventListener("mouseleave", start);
  host.addEventListener("focusin", stop);
  host.addEventListener("focusout", start);
  document.addEventListener("visibilitychange", () =>
    document.hidden ? stop() : start(),
  );

  start();
  return stop;
}

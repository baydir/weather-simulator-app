/**
 * The rotating question: what it builds, and what it exposes at a given moment.
 *
 * Not the timer. `rotate` wires intervals, pointer events and a media query,
 * none of which is arithmetic — so the module keeps the decidable part apart and
 * this file takes that on: one node per question, one of them current, and the
 * heading reading as exactly one sentence rather than ten in a row.
 */

import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { install, reads } from "./dom-stub.js";

install();

const { build, next, reveal } = await import("../../web/static/js/prompt.js");
const { texts } = await import("../../web/static/js/i18n.js");

const THREE = ["Une ?", "Deux ?", "Trois ?"];

describe("the order", () => {
  it("comes back to the first after the last", () => {
    assert.equal(next(0, 3), 1);
    assert.equal(next(1, 3), 2);
    assert.equal(next(2, 3), 0);
  });

  it("stays put on a single question", () => {
    assert.equal(next(0, 1), 0);
  });

  it("does not divide by an empty list", () => {
    // A dictionary that has lost its questions must leave the banner blank, not
    // take the page down.
    assert.equal(next(0, 0), 0);
  });
});

describe("the stack", () => {
  it("gives every question a node of its own", () => {
    const nodes = build(THREE);
    assert.equal(nodes.length, 3);
    assert.deepEqual(
      nodes.map((node) => node.textContent),
      THREE,
    );
    assert.ok(nodes.every((node) => node.className === "prompt-item"));
  });

  it("builds nothing from nothing", () => {
    assert.deepEqual(build([]), []);
  });
});

describe("what is exposed", () => {
  it("marks one node current and no other", () => {
    const nodes = build(THREE);
    reveal(nodes, 1);
    assert.deepEqual(
      nodes.map((node) => node.classList.contains("is-current")),
      [false, true, false],
    );
  });

  it("hides the rest from the accessibility tree", () => {
    // The whole reason the heading may change at all: read aloud it must be one
    // question, not the list.
    const nodes = build(THREE);
    reveal(nodes, 2);
    const heading = { className: "", textContent: "", attrs: {}, children: nodes };
    assert.equal(reads(heading), "Trois ?");
  });

  it("takes the hiding back when a node becomes current again", () => {
    const nodes = build(THREE);
    reveal(nodes, 0);
    reveal(nodes, 1);
    reveal(nodes, 0);
    assert.equal(nodes[0].attrs["aria-hidden"], undefined);
    assert.equal(nodes[1].attrs["aria-hidden"], "true");
  });
});

describe("the questions themselves", () => {
  it("are there, and each one asks something", () => {
    assert.ok(texts.home.questions.length >= 1);
    assert.ok(texts.home.questions.every((question) => question.trim().endsWith("?")));
  });

  it("leave the promise to the subtitle", () => {
    // The heading asks; the line under it answers what the site does. What the
    // answer must keep is the verb: rule 1 names "simulation" among the terms
    // it allows, and it is the verb that makes the sentence an offer to try
    // rather than a claim about a day. present.test.js covers the words the
    // rule forbids; this covers the one it needs.
    assert.match(texts.home.promise, /^Simulez /);
  });
});

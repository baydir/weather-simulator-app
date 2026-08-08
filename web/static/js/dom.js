/**
 * The two things both pages need to put text on screen.
 *
 * `applyTexts` is what lets the HTML stay static while every sentence still
 * lives in i18n.js: a page marks a slot with `data-text="form.place"` and this
 * fills it. No sentence in a page file, no page file in the dictionary.
 *
 * `el` builds a node with `textContent`, never `innerHTML`. The place name
 * travels in the query string, so it is visitor input arriving as text — the
 * one habit that keeps it from being anything else.
 */

import { texts } from "./i18n.js";

/** "form.place" → the string at texts.form.place, or undefined. */
export function lookup(path) {
  return path.split(".").reduce((node, key) => node?.[key], texts);
}

/**
 * Fill every slot marked in the markup.
 *
 * `data-text="a.b"` sets the element's text; `data-attr-placeholder="a.b"` sets
 * its placeholder, and so on for any attribute.
 */
export function applyTexts(root = document) {
  for (const node of root.querySelectorAll("[data-text]")) {
    node.textContent = lookup(node.dataset.text) ?? "";
  }
  for (const node of root.querySelectorAll("*")) {
    for (const [key, path] of Object.entries(node.dataset)) {
      if (key.startsWith("attr")) {
        // dataset gives back "attrAriaLabel"; the attribute is "aria-label".
        const name = key
          .slice(4)
          .replace(/[A-Z]/g, (letter) => `-${letter.toLowerCase()}`)
          .replace(/^-/, "");
        node.setAttribute(name, lookup(path) ?? "");
      }
    }
  }
}

/** A node, its classes, its text, its children. */
export function el(tag, { className, text, attrs } = {}, children = []) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  for (const [name, value] of Object.entries(attrs ?? {})) {
    // An attribute with nothing to say is left off rather than set empty: an
    // `aria-label=""` is not the absence of a label, it is an empty one.
    if (value !== undefined && value !== null && value !== "") node.setAttribute(name, value);
  }
  node.append(...children);
  return node;
}

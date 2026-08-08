/**
 * Just enough `document` for band.js to build its nodes outside a browser.
 *
 * Four methods, because that is all dom.js touches. Not a DOM implementation
 * and not trying to be one: the point is to check what the strip *says* — the
 * seam falling on the right day, the month named only where it turns, a gap
 * showing a dash — none of which needs layout, styling or events.
 *
 * It has to be installed before band.js is imported, since `el` reaches for the
 * global on its first call.
 */

class StubNode {
  constructor(tag) {
    this.tag = tag;
    this.className = "";
    this.textContent = "";
    this.attrs = {};
    this.children = [];
  }

  setAttribute(name, value) {
    this.attrs[name] = String(value);
  }

  append(...nodes) {
    this.children.push(...nodes);
  }
}

export function install() {
  globalThis.document = { createElement: (tag) => new StubNode(tag) };
}

/** Every node in the tree, the root included. */
export function walk(node) {
  return [node, ...node.children.flatMap(walk)];
}

/** The nodes carrying a given class, anywhere below `node`. */
export function byClass(node, name) {
  return walk(node).filter((child) => child.className.split(" ").includes(name));
}

/** The text of the first node carrying that class, or undefined. */
export function textOf(node, name) {
  return byClass(node, name)[0]?.textContent;
}

/** Everything the card says, in reading order — what a screen reader gets. */
export function reads(node) {
  return walk(node)
    .filter((child) => child.attrs["aria-hidden"] !== "true")
    .map((child) => child.textContent)
    .filter(Boolean)
    .join(" ");
}

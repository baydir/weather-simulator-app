/**
 * Just enough `document` for the display modules to build their nodes outside a
 * browser.
 *
 * Only what they actually touch. Not a DOM implementation and not trying to be
 * one: the point is to check what a page *says* — the seam falling on the right
 * day, the month named only where it turns, a gap showing a dash, one question
 * exposed out of ten — none of which needs layout, styling or events.
 *
 * `classList` and `removeAttribute` arrived with prompt.js, whose whole
 * accessibility guarantee is which node carries `aria-hidden` at a given moment.
 * That is a claim about the tree, so it is checkable here.
 *
 * It has to be installed before the module under test is imported, since `el`
 * reaches for the global on its first call.
 */

class StubNode {
  constructor(tag, namespace = null) {
    this.tag = tag;
    // Kept so that a test can say a mark was built as SVG and not as an HTML
    // element wearing an SVG name — the one failure that is invisible on screen.
    this.namespace = namespace;
    this.className = "";
    this.textContent = "";
    this.attrs = {};
    this.children = [];
    this.classList = {
      toggle: (name, on) => {
        const classes = new Set(this.className.split(" ").filter(Boolean));
        if (on) classes.add(name);
        else classes.delete(name);
        this.className = [...classes].join(" ");
      },
      contains: (name) => this.className.split(" ").includes(name),
    };
  }

  setAttribute(name, value) {
    // `class` is where the classes actually live now, `el` having moved off the
    // property so that the same builder serves SVG. Everything here that reads
    // a class — `classList`, `byClass`, the tests comparing `className` — goes
    // on working, which is the point of catching it at the one door.
    if (name === "class") this.className = String(value);
    this.attrs[name] = String(value);
  }

  removeAttribute(name) {
    delete this.attrs[name];
  }

  append(...nodes) {
    this.children.push(...nodes);
  }
}

export function install() {
  globalThis.document = {
    createElement: (tag) => new StubNode(tag),
    createElementNS: (namespace, tag) => new StubNode(tag, namespace),
  };
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

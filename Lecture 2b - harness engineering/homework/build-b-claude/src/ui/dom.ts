/** Something that can be appended as a child; falsy values are skipped so callers can use `cond && node`. */
export type Child = Node | string | null | undefined | false;

type Attributes = Record<string, string | number>;

/** Creates an HTML element with attributes and children. */
export function html<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  attrs: Attributes = {},
  children: Child[] = [],
): HTMLElementTagNameMap[K] {
  return fill(document.createElement(tag), attrs, children);
}

/** Creates an SVG element with attributes and children. */
export function svg<K extends keyof SVGElementTagNameMap>(
  tag: K,
  attrs: Attributes = {},
  children: Child[] = [],
): SVGElementTagNameMap[K] {
  return fill(document.createElementNS(SVG_NAMESPACE, tag), attrs, children);
}

/** A small square in a player's color, shown next to their name. */
export function swatch(color: string): HTMLSpanElement {
  return html('span', { class: 'swatch', style: `background: ${color}` });
}

const SVG_NAMESPACE = 'http://www.w3.org/2000/svg';

function fill<E extends Element>(element: E, attrs: Attributes, children: Child[]): E {
  for (const [name, value] of Object.entries(attrs)) element.setAttribute(name, String(value));
  for (const child of children) {
    if (child) element.append(child);
  }
  return element;
}

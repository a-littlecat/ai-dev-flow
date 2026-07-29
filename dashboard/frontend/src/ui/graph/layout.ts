/**
 * Layered DAG layout for the task relationship graph.
 *
 * - Directional edges (depends_on / parent / replaces / discovered_from) flow
 *   left -> right along the display direction (prerequisite -> dependent ...).
 * - Cycles are broken by dropping DFS back edges from layering; dropped edges
 *   are still drawn (flagged) so dependency-cycle data stays visible.
 * - Symmetric conflicts_with edges do not participate in layering.
 * - Ordering inside a layer uses a few barycenter sweeps to reduce crossings.
 * No external layout dependency: small, reviewable and deterministic.
 */
import type { RelationshipEdge } from "../../generated/contracts.types";

export const NODE_WIDTH = 244;
export const NODE_HEIGHT = 100;
export const LAYER_GAP = 110;
export const ROW_GAP = 30;

export interface LayoutNode {
  taskId: string;
  x: number;
  y: number;
  layer: number;
  order: number;
}

export interface GraphLayout {
  nodes: Map<string, LayoutNode>;
  /** edge ids removed from layering because they close a cycle */
  cycleEdgeIds: Set<string>;
  width: number;
  height: number;
}

interface LayeringEdge {
  edgeId: string;
  from: string; // upstream (display source)
  to: string; // downstream (display target)
}

export function layeringFlow(edge: RelationshipEdge): { from: string; to: string } | null {
  if (edge.type === "conflicts_with") {
    return null;
  }
  // Every directional edge type displays target -> source.
  return { from: edge.target_task_id, to: edge.source_task_id };
}

export function layoutGraph(taskIds: string[], edges: RelationshipEdge[]): GraphLayout {
  const nodes = new Map<string, LayoutNode>();
  for (const taskId of taskIds) {
    nodes.set(taskId, { taskId, x: 0, y: 0, layer: 0, order: 0 });
  }
  const layeringEdges: LayeringEdge[] = [];
  for (const edge of edges) {
    const flow = layeringFlow(edge);
    if (flow && nodes.has(flow.from) && nodes.has(flow.to) && flow.from !== flow.to) {
      layeringEdges.push({ edgeId: edge.edge_id, ...flow });
    }
  }

  const cycleEdgeIds = new Set<string>();
  const acyclic = breakCycles(nodes, layeringEdges, cycleEdgeIds);
  assignLayers(nodes, acyclic);
  orderLayers(nodes, acyclic);
  position(nodes);

  let width = 0;
  let height = 0;
  for (const node of nodes.values()) {
    width = Math.max(width, node.x + NODE_WIDTH);
    height = Math.max(height, node.y + NODE_HEIGHT);
  }
  return { nodes, cycleEdgeIds, width: width + LAYER_GAP, height: height + ROW_GAP };
}

function buildAdjacency(
  nodes: Map<string, LayoutNode>,
  edges: LayeringEdge[],
): Map<string, { edgeId: string; to: string }[]> {
  const adjacency = new Map<string, { edgeId: string; to: string }[]>();
  for (const taskId of nodes.keys()) {
    adjacency.set(taskId, []);
  }
  for (const edge of edges) {
    adjacency.get(edge.from)?.push({ edgeId: edge.edgeId, to: edge.to });
  }
  return adjacency;
}

/** DFS from every node; remove back edges (first encountered) to make the graph acyclic. */
function breakCycles(
  nodes: Map<string, LayoutNode>,
  edges: LayeringEdge[],
  cycleEdgeIds: Set<string>,
): LayeringEdge[] {
  const WHITE = 0;
  const GRAY = 1;
  const BLACK = 2;
  const color = new Map<string, number>();
  for (const taskId of nodes.keys()) {
    color.set(taskId, WHITE);
  }
  const removed = new Set<string>();

  const visit = (start: string) => {
    const stack: { node: string; edgeIndex: number; edges: { edgeId: string; to: string }[] }[] = [];
    color.set(start, GRAY);
    stack.push({ node: start, edgeIndex: 0, edges: [] });
    const adjacency = buildAdjacency(nodes, edges.filter((edge) => !removed.has(edge.edgeId)));
    stack[0]!.edges = adjacency.get(start) ?? [];
    while (stack.length > 0) {
      const frame = stack[stack.length - 1]!;
      if (frame.edgeIndex >= frame.edges.length) {
        color.set(frame.node, BLACK);
        stack.pop();
        continue;
      }
      const next = frame.edges[frame.edgeIndex]!;
      frame.edgeIndex += 1;
      const nextColor = color.get(next.to) ?? WHITE;
      if (nextColor === GRAY) {
        removed.add(next.edgeId);
        cycleEdgeIds.add(next.edgeId);
        // Remove the back edge from the current frame's remaining scan.
        frame.edges = frame.edges.filter((candidate) => candidate.edgeId !== next.edgeId);
        continue;
      }
      if (nextColor === WHITE) {
        color.set(next.to, GRAY);
        stack.push({ node: next.to, edgeIndex: 0, edges: adjacency.get(next.to) ?? [] });
      }
    }
  };

  for (const taskId of nodes.keys()) {
    if ((color.get(taskId) ?? WHITE) === WHITE) {
      visit(taskId);
    }
  }
  return edges.filter((edge) => !removed.has(edge.edgeId));
}

/** Longest-path layering over the acyclic remainder. */
function assignLayers(nodes: Map<string, LayoutNode>, edges: LayeringEdge[]): void {
  const indegree = new Map<string, number>();
  const outgoing = new Map<string, string[]>();
  for (const taskId of nodes.keys()) {
    indegree.set(taskId, 0);
    outgoing.set(taskId, []);
  }
  for (const edge of edges) {
    indegree.set(edge.to, (indegree.get(edge.to) ?? 0) + 1);
    outgoing.get(edge.from)?.push(edge.to);
  }
  const queue = taskIdsSorted(nodes).filter((taskId) => (indegree.get(taskId) ?? 0) === 0);
  const visited = new Set<string>();
  while (queue.length > 0) {
    const current = queue.shift()!;
    if (visited.has(current)) {
      continue;
    }
    visited.add(current);
    const currentLayer = nodes.get(current)?.layer ?? 0;
    for (const next of outgoing.get(current) ?? []) {
      const nextNode = nodes.get(next);
      if (nextNode && nextNode.layer < currentLayer + 1) {
        nextNode.layer = currentLayer + 1;
      }
      indegree.set(next, (indegree.get(next) ?? 1) - 1);
      if ((indegree.get(next) ?? 0) <= 0) {
        queue.push(next);
      }
    }
  }
}

function taskIdsSorted(nodes: Map<string, LayoutNode>): string[] {
  return [...nodes.keys()].sort((a, b) => a.localeCompare(b));
}

/** Barycenter sweeps to reduce edge crossings. */
function orderLayers(nodes: Map<string, LayoutNode>, edges: LayeringEdge[]): void {
  const layers = new Map<number, string[]>();
  for (const node of nodes.values()) {
    const list = layers.get(node.layer) ?? [];
    list.push(node.taskId);
    layers.set(node.layer, list);
  }
  for (const list of layers.values()) {
    list.sort((a, b) => a.localeCompare(b));
  }
  const positionOf = new Map<string, number>();
  const index = () => {
    for (const list of layers.values()) {
      list.forEach((taskId, i) => positionOf.set(taskId, i));
    }
  };
  const predecessors = new Map<string, string[]>();
  const successors = new Map<string, string[]>();
  for (const edge of edges) {
    (predecessors.get(edge.to) ?? predecessors.set(edge.to, []).get(edge.to)!).push(edge.from);
    (successors.get(edge.from) ?? successors.set(edge.from, []).get(edge.from)!).push(edge.to);
  }
  const barycenter = (taskId: string, neighbors: Map<string, string[]>): number | null => {
    const positions = (neighbors.get(taskId) ?? [])
      .map((other) => positionOf.get(other))
      .filter((value): value is number => value !== undefined);
    if (positions.length === 0) {
      return null;
    }
    return positions.reduce((sum, value) => sum + value, 0) / positions.length;
  };
  const sortedLayerKeys = [...layers.keys()].sort((a, b) => a - b);
  for (let sweep = 0; sweep < 6; sweep += 1) {
    index();
    const forward = sweep % 2 === 0;
    for (const layerKey of forward ? sortedLayerKeys : [...sortedLayerKeys].reverse()) {
      const list = layers.get(layerKey)!;
      const neighborMap = forward ? predecessors : successors;
      list.sort((a, b) => {
        const ba = barycenter(a, neighborMap);
        const bb = barycenter(b, neighborMap);
        if (ba === null && bb === null) {
          return a.localeCompare(b);
        }
        if (ba === null) {
          return 1;
        }
        if (bb === null) {
          return -1;
        }
        return ba - bb || a.localeCompare(b);
      });
    }
  }
  index();
  for (const [layerKey, list] of layers) {
    list.forEach((taskId, order) => {
      const node = nodes.get(taskId);
      if (node) {
        node.layer = layerKey;
        node.order = order;
      }
    });
  }
}

function position(nodes: Map<string, LayoutNode>): void {
  const layerSizes = new Map<number, number>();
  let maxRows = 0;
  for (const node of nodes.values()) {
    const size = (layerSizes.get(node.layer) ?? 0) + 1;
    layerSizes.set(node.layer, size);
    maxRows = Math.max(maxRows, size);
  }
  const totalHeight = maxRows * (NODE_HEIGHT + ROW_GAP);
  const layerOffset = new Map<number, number>();
  for (const [layer, size] of layerSizes) {
    layerOffset.set(layer, (totalHeight - size * (NODE_HEIGHT + ROW_GAP)) / 2);
  }
  for (const node of nodes.values()) {
    node.x = LAYER_GAP / 2 + node.layer * (NODE_WIDTH + LAYER_GAP);
    node.y = (layerOffset.get(node.layer) ?? 0) + node.order * (NODE_HEIGHT + ROW_GAP) + ROW_GAP / 2;
  }
}

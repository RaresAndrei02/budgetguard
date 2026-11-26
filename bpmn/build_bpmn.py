#!/usr/bin/env python3
"""Generate the two BudgetGuard BPMN 2.0 diagrams (process model + DI).

Output (open in https://demo.bpmn.io or Camunda Modeler):
    bpmn/flux1_cerere_achizitie.bpmn
    bpmn/flux2_import_analiza.bpmn

Layout: elements sit on a grid (column = process step, row = lane / sub-row);
sequence flows are routed orthogonally from explicit ports.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

OUT_DIR = Path(__file__).resolve().parent

SIZES = {"task": (100, 80), "gateway": (50, 50), "event": (36, 36), "store": (50, 50)}
TASKS = {"task", "serviceTask", "userTask", "sendTask", "scriptTask", "subProcess"}
EVENTS = {"startEvent", "endEvent", "boundaryEvent"}

NS = (
    'xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" '
    'xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" '
    'xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" '
    'xmlns:di="http://www.omg.org/spec/DD/20100524/DI" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
)


# Diagrams are emitted without diacritics / typographic characters (user preference).
_ASCII_MAP = str.maketrans({"„": "'", "”": "'", "“": "'", "–": "-", "—": "-", "…": "...", "→": "->"})


def to_ascii(text: str) -> str:
    text = text.translate(_ASCII_MAP)
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


# --------------------------------------------------------------------------- model


@dataclass
class Node:
    id: str
    kind: str
    name: str
    x: float
    y: float
    w: float
    h: float
    parent: str | None  # process id / subprocess id (None for participants)
    lane: str | None = None
    attrs: dict = field(default_factory=dict)
    body: list = field(default_factory=list)  # event definitions, loop characteristics
    label: tuple | None = None  # external label bounds
    incoming: list = field(default_factory=list)
    outgoing: list = field(default_factory=list)
    in_assoc: list = field(default_factory=list)  # (assoc_id, source store id)
    out_assoc: list = field(default_factory=list)  # (assoc_id, target store id)

    @property
    def cx(self):
        return self.x + self.w / 2

    @property
    def cy(self):
        return self.y + self.h / 2

    def port(self, side):
        off = 0
        if isinstance(side, tuple):
            side, off = side
        return {
            "l": (self.x, self.cy + off),
            "r": (self.x + self.w, self.cy + off),
            "t": (self.cx + off, self.y),
            "b": (self.cx + off, self.y + self.h),
        }[side]


def _side(s):
    return s[0] if isinstance(s, tuple) else s


def _auto(p0, p1, ss, ts):
    """Orthogonal intermediate points between two ports."""
    (x0, y0), (x1, y1) = p0, p1
    h0, h1 = ss in "lr", ts in "lr"
    if h0 and h1:
        if abs(y0 - y1) < 1:
            return []
        mx = (x0 + x1) / 2
        return [(mx, y0), (mx, y1)]
    if not h0 and h1:
        return [(x0, y1)]
    if h0 and not h1:
        return [(x1, y0)]
    if abs(x0 - x1) < 1:
        return []
    my = (y0 + y1) / 2
    return [(x0, my), (x1, my)]


def _flow_label(wps, name):
    """Small label box next to the start of an edge."""
    (x0, y0), (x1, y1) = wps[0], wps[1]
    w = max(24, 7 * len(name))
    if abs(x0 - x1) < 1:  # vertical first segment
        dy = 6 if y1 > y0 else -22
        return (x0 + 5, y0 + dy, w, 14)
    dx = 6 if x1 > x0 else -w - 6
    return (x0 + dx, y0 - 18, w, 14)


class Model:
    def __init__(self, defs_id: str):
        self.defs_id = defs_id
        self.nodes: dict[str, Node] = {}
        self.participants: list[Node] = []
        self.lanes: list[tuple] = []  # (id, name, process, x, y, w, h)
        self.processes: list[str] = []
        self.flows: list[dict] = []
        self.msgflows: list[dict] = []
        self.assoc_edges: list[tuple] = []  # (id, waypoints)
        self.annotations: list[Node] = []
        self.ann_links: list[dict] = []
        self.errors: list[tuple] = []  # (id, name, code)

    # ---- building helpers
    def node(self, id, kind, name, cx, cy, parent, lane=None, size=None, label=None, **kw):
        if kind in TASKS:
            base = "task"
        elif "Gateway" in kind:
            base = "gateway"
        elif kind in EVENTS:
            base = "event"
        else:
            base = "store"
        w, h = size or SIZES[base]
        n = Node(id, kind, name, cx - w / 2, cy - h / 2, w, h, parent, lane, **kw)
        if label is None and base in ("event", "gateway") and name:
            label = ("below",)
        n.label = self._label_box(n, label) if label else None
        self.nodes[id] = n
        return n

    @staticmethod
    def _label_box(n, spec):
        kind = spec[0]
        if kind == "below":
            return (n.cx - 50, n.y + n.h + 4, 100, 27)
        if kind == "above":
            return (n.cx - 50, n.y - 31, 100, 27)
        if kind == "right":
            return (n.x + n.w + 4, n.cy - 10, spec[1] if len(spec) > 1 else 90, 27)
        if kind == "left":
            w = spec[1] if len(spec) > 1 else 90
            return (n.x - w - 4, n.cy - 10, w, 27)
        if kind == "abs":
            return spec[1]
        raise ValueError(spec)

    def participant(self, id, name, x, y, w, h, process=None):
        n = Node(id, "participant", name, x, y, w, h, None, attrs={"processRef": process} if process else {})
        self.participants.append(n)
        self.nodes[id] = n
        return n

    def lane(self, id, name, process, x, y, w, h):
        self.lanes.append((id, name, process, x, y, w, h))

    def flow(self, src, tgt, name="", ss="r", ts="l", via=None):
        s, t = self.nodes[src], self.nodes[tgt]
        fid = f"Flow_{src}_{tgt}"
        p0, p1 = s.port(ss), t.port(ts)
        mids = via if via is not None else _auto(p0, p1, _side(ss), _side(ts))
        wps = [p0, *mids, p1]
        s.outgoing.append(fid)
        t.incoming.append(fid)
        self.flows.append(
            dict(id=fid, name=name, src=src, tgt=tgt, parent=s.parent, wps=wps,
                 label=_flow_label(wps, name) if name else None)
        )

    def chain(self, *ids):
        for a, b in zip(ids, ids[1:]):
            self.flow(a, b)

    def message(self, src, tgt, name, x, label_side="left", frac=0.5, gap=6):
        """Vertical message flow at abscissa x between two vertically separated shapes."""
        s, t = self.nodes[src], self.nodes[tgt]
        if s.y < t.y:
            p0, p1 = (x, s.y + s.h), (x, t.y)
        else:
            p0, p1 = (x, s.y), (x, t.y + t.h)
        my = p0[1] + (p1[1] - p0[1]) * frac
        w = 120
        lab = (x - w - gap, my - 14, w, 27) if label_side == "left" else (x + gap, my - 14, w, 27)
        self.msgflows.append(dict(id=f"MsgFlow_{src}_{tgt}", name=name, src=src, tgt=tgt, wps=[p0, p1], label=lab))

    def data_out(self, task, store, dx=0):
        t, s = self.nodes[task], self.nodes[store]
        aid = f"DataOut_{task}_{store}"
        t.out_assoc.append((aid, store))
        self.assoc_edges.append((aid, self._straight(t, s, dx, 0)))

    def data_in(self, store, task, dx=0):
        t, s = self.nodes[task], self.nodes[store]
        aid = f"DataIn_{store}_{task}"
        t.in_assoc.append((aid, store))
        self.assoc_edges.append((aid, self._straight(s, t, 0, dx)))

    @staticmethod
    def _straight(a, b, dxa=0, dxb=0):
        if a.y + a.h <= b.y:
            return [(a.cx + dxa, a.y + a.h), (b.cx + dxb, b.y)]
        return [(a.cx + dxa, a.y), (b.cx + dxb, b.y + b.h)]

    def annotation(self, id, text, x, y, w, h, parent, target=None, target_port="t"):
        n = Node(id, "textAnnotation", text, x, y, w, h, parent)
        self.annotations.append(n)
        self.nodes[id] = n
        if target:
            t = self.nodes[target]
            tp = t.port(target_port)
            start = (x + 30, y) if tp[1] < y else (x + 30, y + h)
            self.ann_links.append(
                dict(id=f"Assoc_{id}_{target}", src=id, tgt=target, parent=parent, wps=[start, tp])
            )

    # ---- XML serialisation
    def _node_xml(self, n: Node, ind: str) -> list[str]:
        attrs = {"id": n.id}
        if n.name:
            attrs["name"] = n.name
        attrs.update(n.attrs)
        a = " ".join(f"{k}={quoteattr(str(v))}" for k, v in attrs.items())
        inner = [f"<bpmn:incoming>{f}</bpmn:incoming>" for f in n.incoming]
        inner += [f"<bpmn:outgoing>{f}</bpmn:outgoing>" for f in n.outgoing]
        if n.in_assoc:
            inner.append(f'<bpmn:property id="Property_{n.id}" name="__targetRef_placeholder" />')
            for aid, src in n.in_assoc:
                inner.append(
                    f'<bpmn:dataInputAssociation id="{aid}"><bpmn:sourceRef>{src}</bpmn:sourceRef>'
                    f"<bpmn:targetRef>Property_{n.id}</bpmn:targetRef></bpmn:dataInputAssociation>"
                )
        for aid, tgt in n.out_assoc:
            inner.append(
                f'<bpmn:dataOutputAssociation id="{aid}"><bpmn:targetRef>{tgt}</bpmn:targetRef></bpmn:dataOutputAssociation>'
            )
        inner += n.body
        lines = [ind + l for l in inner]
        if n.kind == "subProcess":
            lines += self._children(n.id, ind)
        if not lines:
            return [f"{ind[:-2]}<bpmn:{n.kind} {a} />"]
        return [f"{ind[:-2]}<bpmn:{n.kind} {a}>", *lines, f"{ind[:-2]}</bpmn:{n.kind}>"]

    def _children(self, container: str, ind: str) -> list[str]:
        out = []
        for n in self.nodes.values():
            if n.parent == container and n.kind not in ("participant", "textAnnotation"):
                out += self._node_xml(n, ind + "  ")
        for f in self.flows:
            if f["parent"] == container:
                nm = f' name={quoteattr(f["name"])}' if f["name"] else ""
                out.append(f'{ind}<bpmn:sequenceFlow id="{f["id"]}"{nm} sourceRef="{f["src"]}" targetRef="{f["tgt"]}" />')
        for n in self.annotations:
            if n.parent == container:
                out.append(f'{ind}<bpmn:textAnnotation id="{n.id}"><bpmn:text>{escape(n.name)}</bpmn:text></bpmn:textAnnotation>')
        for l in self.ann_links:
            if l["parent"] == container:
                out.append(f'{ind}<bpmn:association id="{l["id"]}" sourceRef="{l["src"]}" targetRef="{l["tgt"]}" />')
        return out

    @staticmethod
    def _b(x, y, w, h):
        return f'<dc:Bounds x="{round(x)}" y="{round(y)}" width="{round(w)}" height="{round(h)}" />'

    def _edge(self, eid, wps, label=None):
        pts = "".join(f'<di:waypoint x="{round(x)}" y="{round(y)}" />' for x, y in wps)
        lab = f"<bpmndi:BPMNLabel>{self._b(*label)}</bpmndi:BPMNLabel>" if label else ""
        return f'    <bpmndi:BPMNEdge id="{eid}_di" bpmnElement="{eid}">{pts}{lab}</bpmndi:BPMNEdge>'

    def to_xml(self) -> str:
        o = ['<?xml version="1.0" encoding="UTF-8"?>',
             f'<bpmn:definitions {NS} id="{self.defs_id}" targetNamespace="http://bpmn.io/schema/bpmn" '
             'exporter="BudgetGuard build_bpmn.py" exporterVersion="1.0">']
        collab = f"Collaboration_{self.defs_id}"
        o.append(f'  <bpmn:collaboration id="{collab}">')
        for p in self.participants:
            pr = f' processRef="{p.attrs["processRef"]}"' if "processRef" in p.attrs else ""
            o.append(f'    <bpmn:participant id="{p.id}" name={quoteattr(p.name)}{pr} />')
        for m in self.msgflows:
            o.append(f'    <bpmn:messageFlow id="{m["id"]}" name={quoteattr(m["name"])} sourceRef="{m["src"]}" targetRef="{m["tgt"]}" />')
        o.append("  </bpmn:collaboration>")
        for proc in self.processes:
            o.append(f'  <bpmn:process id="{proc}" isExecutable="false">')
            lanes = [l for l in self.lanes if l[2] == proc]
            if lanes:
                o.append(f'    <bpmn:laneSet id="LaneSet_{proc}">')
                for lid, lname, *_ in lanes:
                    o.append(f'      <bpmn:lane id="{lid}" name={quoteattr(lname)}>')
                    for n in self.nodes.values():
                        if n.lane == lid and n.parent == proc:
                            o.append(f"        <bpmn:flowNodeRef>{n.id}</bpmn:flowNodeRef>")
                    o.append("      </bpmn:lane>")
                o.append("    </bpmn:laneSet>")
            o += self._children(proc, "    ")
            o.append("  </bpmn:process>")
        for eid, name, code in self.errors:
            o.append(f'  <bpmn:error id="{eid}" name={quoteattr(name)} errorCode="{code}" />')

        # ---- diagram interchange
        o.append(f'  <bpmndi:BPMNDiagram id="Diagram_{self.defs_id}">')
        o.append(f'    <bpmndi:BPMNPlane id="Plane_{self.defs_id}" bpmnElement="{collab}">')
        for p in self.participants:
            o.append(f'    <bpmndi:BPMNShape id="{p.id}_di" bpmnElement="{p.id}" isHorizontal="true">{self._b(p.x, p.y, p.w, p.h)}</bpmndi:BPMNShape>')
        for lid, _, _, x, y, w, h in self.lanes:
            o.append(f'    <bpmndi:BPMNShape id="{lid}_di" bpmnElement="{lid}" isHorizontal="true">{self._b(x, y, w, h)}</bpmndi:BPMNShape>')
        for n in self.nodes.values():
            if n.kind == "participant":
                continue
            extra = ""
            if n.kind == "exclusiveGateway":
                extra = ' isMarkerVisible="true"'
            if n.kind == "subProcess":
                extra = ' isExpanded="true"'
            lab = f"<bpmndi:BPMNLabel>{self._b(*n.label)}</bpmndi:BPMNLabel>" if n.label else ""
            o.append(f'    <bpmndi:BPMNShape id="{n.id}_di" bpmnElement="{n.id}"{extra}>{self._b(n.x, n.y, n.w, n.h)}{lab}</bpmndi:BPMNShape>')
        for f in self.flows:
            o.append(self._edge(f["id"], f["wps"], f["label"]))
        for m in self.msgflows:
            o.append(self._edge(m["id"], m["wps"], m["label"]))
        for aid, wps in self.assoc_edges:
            o.append(self._edge(aid, wps))
        for l in self.ann_links:
            o.append(self._edge(l["id"], l["wps"]))
        o.append("    </bpmndi:BPMNPlane>")
        o.append("  </bpmndi:BPMNDiagram>")
        o.append("</bpmn:definitions>")
        return "\n".join(o) + "\n"


# --------------------------------------------------------------------------- shared bits

MSG_START = '<bpmn:messageEventDefinition id="MessageEventDefinition_{0}" />'
MI_SEQ = '<bpmn:multiInstanceLoopCharacteristics isSequential="true" />'


def timer_def(i, duration):
    return (f'<bpmn:timerEventDefinition id="TimerEventDefinition_{i}">'
            f'<bpmn:timeDuration xsi:type="bpmn:tFormalExpression">{duration}</bpmn:timeDuration>'
            "</bpmn:timerEventDefinition>")


def error_def(i, ref):
    return f'<bpmn:errorEventDefinition id="ErrorEventDefinition_{i}" errorRef="{ref}" />'


# --------------------------------------------------------------------------- BPMN 1


def build_flux1() -> Model:
    m = Model("Definitions_Flux1")
    P = "Process_Flux1"
    m.processes.append(P)

    COL, X0 = 150, 270
    cx = lambda c: X0 + c * COL  # noqa: E731
    POOL_X, POOL_Y = 150, 150
    last_col = 21
    pool_w = cx(last_col) + 100 - POOL_X

    lane_defs = [
        ("Lane_Solicitant", "Solicitant", 130),
        ("Lane_Sistem", "Sistem BudgetGuard (Power Automate)", 380),
        ("Lane_Manager", "Manager centru de cost", 130),
        ("Lane_Controlling", "Controlling", 130),
        ("Lane_Financiar", "Director financiar", 130),
        ("Lane_CFO", "CFO", 130),
    ]
    y = POOL_Y
    ly = {}
    for lid, name, h in lane_defs:
        m.lane(lid, name, P, POOL_X + 30, y, pool_w - 30, h)
        ly[lid] = (y, h)
        y += h
    pool_h = y - POOL_Y
    m.participant("Participant_Vestra", "Vestra Retail SRL – BudgetGuard (Flux 1: cerere de achiziție)",
                  POOL_X, POOL_Y, pool_w, pool_h, P)
    m.participant("Participant_ANAF", "ANAF – serviciu web TVA v9", cx(2) + 70 - 260, 40, 260, 60)
    m.participant("Participant_BNR", "BNR – curs valutar zilnic", cx(3) - 70, 40, 260, 60)

    mid = lambda lid: ly[lid][0] + ly[lid][1] / 2  # noqa: E731
    sy = ly["Lane_Sistem"][0]
    ROW0, ROW1, ROW2 = sy + 60, sy + 190, sy + 310  # data stores / happy path / rejection path
    S = "Lane_Sistem"

    # requester
    m.node("Start_Cerere", "startEvent", "Cerere trimisă (Microsoft Forms)", cx(0), mid("Lane_Solicitant"), P,
           "Lane_Solicitant", body=[MSG_START.format("Forms")])

    # registration + validation
    m.node("Task_Inregistrare", "serviceTask", "Înregistrează cererea (ID PR-…, status Nouă)", cx(1), ROW1, P, S)
    m.node("Task_ANAF", "serviceTask", "Validează furnizorul la ANAF (V1, V2, V2b, W3)", cx(2), ROW1, P, S)
    m.node("Task_BNR", "serviceTask", "Curs BNR (rezervă: W4), calculează Valoare_RON (V3)", cx(3), ROW1, P, S)
    m.node("Task_VerificaBuget", "serviceTask", "Verifică data și bugetul (V4, V5, W1, W2)", cx(4), ROW1, P, S)
    m.node("Gateway_DateValide", "exclusiveGateway", "Date valide?", cx(5), ROW1, P, S, label=("above",))
    m.node("Task_StatusInAprobare", "serviceTask", "Setează status „În aprobare”", cx(6), ROW1, P, S)
    m.node("Send_NotifInAprobare", "sendTask", "Notifică solicitantul (email + Teams)", cx(7), ROW1, P, S)

    # validation rejection
    m.node("Task_RespinsaValidare", "serviceTask", "Setează status „Respinsă” (motive validare)", cx(5), ROW2, P, S)
    m.node("Send_NotifRespValidare", "sendTask", "Notifică respingerea (email + Teams)", cx(6), ROW2, P, S)
    m.node("End_RespinsaValidare", "endEvent", "Respinsă la validare", cx(7), ROW2, P, S)

    # sequential approvals
    approvers = [
        ("1", "Lane_Manager", 8, "Aprobare pas 1 – manager CC"),
        ("2", "Lane_Controlling", 10, "Aprobare pas 2 – controlling"),
        ("3", "Lane_Financiar", 12, "Aprobare pas 3 – director financiar"),
    ]
    for k, lane, c, name in approvers:
        m.node(f"User_Aprobare{k}", "userTask", name, cx(c), mid(lane), P, lane)
        lab = ("right", 60) if k in ("1", "2") else ("below",)
        m.node(f"Gateway_Aprobat{k}", "exclusiveGateway", "Aprobat?", cx(c + 1), mid(lane), P, lane, label=lab)
    m.node("Gateway_PesteBuget", "exclusiveGateway", "Peste buget sau > prag CFO?", cx(14), ROW1, P, S, label=("above",))
    m.node("User_Aprobare4", "userTask", "Aprobare pas 4 – CFO", cx(15), mid("Lane_CFO"), P, "Lane_CFO")
    m.node("Gateway_Aprobat4", "exclusiveGateway", "Aprobat?", cx(16), mid("Lane_CFO"), P, "Lane_CFO")

    for k in "1234":
        t = m.nodes[f"User_Aprobare{k}"]
        m.node(f"Timer_Aprobare{k}", "boundaryEvent", "7 zile", t.x + 75, t.y, P, t.lane,
               attrs={"attachedToRef": t.id}, body=[timer_def(k, "P7D")],
               label=("abs", (t.x + 96, t.y - 26, 40, 14)))

    # approved path
    m.node("Gateway_MergeAprobat", "exclusiveGateway", "", cx(17), ROW1, P, S)
    m.node("Task_StatusAprobata", "serviceTask", "Setează status „Aprobată”", cx(18), ROW1, P, S)
    m.node("Task_AngajeazaBuget", "serviceTask", "Angajează suma în buget (Angajat_RON, Ramas_RON)", cx(19), ROW1, P, S)
    m.node("Send_NotifAprobare", "sendTask", "Notifică aprobarea (email + Teams)", cx(20), ROW1, P, S)
    m.node("End_Aprobata", "endEvent", "Cerere aprobată", cx(21), ROW1, P, S)

    # rejected path
    m.node("Gateway_MergeRespins", "exclusiveGateway", "", cx(18), ROW2, P, S)
    m.node("Task_StatusRespinsa", "serviceTask", "Setează status „Respinsă” (motivul aprobatorului)", cx(19), ROW2, P, S)
    m.node("Send_NotifRespingere", "sendTask", "Notifică respingerea (email + Teams)", cx(20), ROW2, P, S)
    m.node("End_Respinsa", "endEvent", "Cerere respinsă", cx(21), ROW2, P, S)

    # data stores (SharePoint lists)
    lab_r = ("right", 95)
    m.node("Store_Cereri1", "dataStoreReference", "Cereri_Achizitie", cx(1), ROW0, P, label=lab_r)
    m.node("Store_Bugete1", "dataStoreReference", "Bugete", cx(4), ROW0, P, label=lab_r)
    m.node("Store_Cereri2", "dataStoreReference", "Cereri_Achizitie", cx(18), ROW0, P, label=lab_r)
    m.node("Store_Bugete2", "dataStoreReference", "Bugete", cx(19), ROW0, P, label=lab_r)

    # sequence flows
    m.flow("Start_Cerere", "Task_Inregistrare", ss="b", ts="l")
    m.chain("Task_Inregistrare", "Task_ANAF", "Task_BNR", "Task_VerificaBuget", "Gateway_DateValide")
    m.flow("Gateway_DateValide", "Task_StatusInAprobare", "Da")
    m.flow("Gateway_DateValide", "Task_RespinsaValidare", "Nu", ss="b", ts="t")
    m.chain("Task_RespinsaValidare", "Send_NotifRespValidare", "End_RespinsaValidare")
    m.chain("Task_StatusInAprobare", "Send_NotifInAprobare", "User_Aprobare1", "Gateway_Aprobat1")
    m.flow("Gateway_Aprobat1", "User_Aprobare2", "Da", ss="b", ts="l")
    m.flow("User_Aprobare2", "Gateway_Aprobat2")
    m.flow("Gateway_Aprobat2", "User_Aprobare3", "Da", ss="b", ts="l")
    m.flow("User_Aprobare3", "Gateway_Aprobat3")
    m.flow("Gateway_Aprobat3", "Gateway_PesteBuget", "Da")
    m.flow("Gateway_PesteBuget", "User_Aprobare4", "Da", ss="b", ts="l")
    m.flow("Gateway_PesteBuget", "Gateway_MergeAprobat", "Nu")
    m.flow("User_Aprobare4", "Gateway_Aprobat4")
    m.flow("Gateway_Aprobat4", "Gateway_MergeAprobat", "Da", ss="r", ts="b")
    for k in "1234":
        m.flow(f"Gateway_Aprobat{k}", "Gateway_MergeRespins", "Nu", ss="t", ts="l")
        m.flow(f"Timer_Aprobare{k}", "Gateway_MergeRespins", ss="t", ts="l")
    m.chain("Gateway_MergeAprobat", "Task_StatusAprobata", "Task_AngajeazaBuget", "Send_NotifAprobare", "End_Aprobata")
    m.chain("Gateway_MergeRespins", "Task_StatusRespinsa", "Send_NotifRespingere", "End_Respinsa")

    # external services
    a, b = m.nodes["Task_ANAF"], m.nodes["Task_BNR"]
    m.message("Task_ANAF", "Participant_ANAF", "CUI + dată", a.cx - 15, "left", 0.75)
    m.message("Participant_ANAF", "Task_ANAF", "date firmă (found / notFound)", a.cx + 15, "left", 0.45, gap=36)
    m.message("Task_BNR", "Participant_BNR", "GET curs", b.cx - 15, "right", 0.75)
    m.message("Participant_BNR", "Task_BNR", "curs EUR / USD", b.cx + 15, "right", 0.45)

    # data associations
    m.data_out("Task_Inregistrare", "Store_Cereri1")
    m.data_in("Store_Bugete1", "Task_VerificaBuget")
    m.data_out("Task_StatusAprobata", "Store_Cereri2")
    m.data_out("Task_AngajeazaBuget", "Store_Bugete2")

    m.annotation(
        "Annotation_Aprobatori",
        "Aprobatorii (manager CC, controlling, financiar, CFO) vin din lista Config; în flux: Do until peste "
        "varAprobatori, cu ieșire la prima respingere. Mod demo (mod_demo = true): un singur "
        "aprobator (adresa din email_bcc).",
        cx(9) - 40, ROW0 - 38, 360, 76, P, target="User_Aprobare1", target_port=("t", -25),
    )
    return m


# --------------------------------------------------------------------------- BPMN 2


def build_flux2() -> Model:
    m = Model("Definitions_Flux2")
    P = "Process_Flux2"
    m.processes.append(P)
    m.errors += [("Error_Import", "Fișier ilizibil, fără înregistrări sau eroare la import", "IMPORT_INVALID"),
                 ("Error_AI", "Eroare la apelul AI (HTTP / timeout / JSON invalid)", "AI_FAILED")]

    POOL_X, POOL_Y = 150, 150
    ROW0, YM, ROW2 = POOL_Y + 60, 470, 790  # data stores / main / error path
    SPW = 740
    icx = lambda x0: [x0 + 50, x0 + 170, x0 + 300, x0 + 430, x0 + 560, x0 + 680]  # noqa: E731

    # main row x positions (centres)
    xs = {}
    x = 218
    xs["start"] = x
    xs["read"] = 340
    xs["gw"] = 465
    xs["ref"] = 590
    sp1_x = 690
    xs["upsert"] = sp1_x + SPW + 100
    xs["err"] = xs["upsert"] + 150
    sp2_x = xs["err"] + 100
    xs["raport"] = sp2_x + SPW + 100
    xs["send"] = xs["raport"] + 150
    xs["muta"] = xs["send"] + 150
    xs["end"] = xs["muta"] + 140
    pool_w = xs["end"] + 70 - POOL_X
    pool_h = ROW2 + 80 - POOL_Y

    m.participant("Participant_BudgetGuard2", "Vestra Retail SRL – BudgetGuard (Flux 2: import realizat și analiză AI)",
                  POOL_X, POOL_Y, pool_w, pool_h, P)

    # top-level nodes
    cond = ('<bpmn:conditionalEventDefinition id="ConditionalEventDefinition_Fisier">'
            '<bpmn:condition xsi:type="bpmn:tFormalExpression">'
            + escape("fișier nou *.json în biblioteca Import_Realizat") +
            "</bpmn:condition></bpmn:conditionalEventDefinition>")
    m.node("Start_FisierNou", "startEvent", "Fișier JSON nou în Import_Realizat", xs["start"], YM, P, body=[cond])
    m.node("Task_CitesteFisier", "serviceTask", "Citește și parsează fișierul JSON", xs["read"], YM, P)
    m.node("Gateway_Lizibil", "exclusiveGateway", "Fișier lizibil?", xs["gw"], YM, P, label=("above",))
    m.node("Send_NotifEsec", "sendTask", "Notifică eșecul importului (email + Teams)", xs["gw"], ROW2, P)
    m.node("End_ImportEsuat", "endEvent", "Import eșuat", xs["gw"] + 130, ROW2, P, body=[error_def("Import", "Error_Import")])
    m.node("Task_Referinte", "serviceTask", "Încarcă nomenclatorul și cursul BNR", xs["ref"], YM, P)

    # sub-process 1: validate each record (multi-instance, sequential)
    sp1_h = 380
    sp1 = m.node("Sub_ValideazaInregistrarea", "subProcess", "Validează înregistrarea (pentru fiecare rând)",
                 sp1_x + SPW / 2, YM, P, size=(SPW, sp1_h), body=[MI_SEQ])
    c = icx(sp1.x)
    SP1 = sp1.id
    m.node("SV_Start", "startEvent", "", c[0], YM, SP1)
    m.node("SV_Verifica", "serviceTask", "Verifică câmpuri, format lună, sumă, monedă, coduri", c[1], YM, SP1)
    m.node("SV_Rezultat", "exclusiveGateway", "Rezultat?", c[2], YM, SP1, label=("abs", (c[2] - 82, YM - 40, 55, 14)))
    m.node("SV_Valid", "task", "Adaugă la valide (conversie în RON)", c[3], YM - 110, SP1)
    m.node("SV_Invalid", "task", "Adaugă eroare cu mesaj personalizat", c[3], YM, SP1)
    m.node("SV_Duplicat", "task", "Marchează duplicatul (prima apariție câștigă)", c[3], YM + 110, SP1)
    m.node("SV_Merge", "exclusiveGateway", "", c[4], YM, SP1)
    m.node("SV_End", "endEvent", "", c[5], YM, SP1)
    m.chain("SV_Start", "SV_Verifica", "SV_Rezultat")
    m.flow("SV_Rezultat", "SV_Valid", "valid", ss="t", ts="l")
    m.flow("SV_Rezultat", "SV_Invalid", "invalid")
    m.flow("SV_Rezultat", "SV_Duplicat", "duplicat", ss="b", ts="l")
    m.flow("SV_Valid", "SV_Merge", ts="t")
    m.flow("SV_Invalid", "SV_Merge")
    m.flow("SV_Duplicat", "SV_Merge", ts="b")
    m.flow("SV_Merge", "SV_End")

    m.node("Task_Upsert", "serviceTask", "Upsert Realizat_Lunar și Bugete; calculează maverick", xs["upsert"], YM, P)
    m.node("Task_SalveazaErori", "serviceTask", "Salvează rândurile respinse în Erori_Import", xs["err"], YM, P)

    # sub-process 2: AI analysis per cost centre (multi-instance, sequential)
    sp2_h = 320
    sp2 = m.node("Sub_AnalizaCC", "subProcess", "Analizează centrul de cost (pentru fiecare CC)",
                 sp2_x + SPW / 2, YM - 130 + sp2_h / 2, P, size=(SPW, sp2_h), body=[MI_SEQ])
    c = icx(sp2.x)
    SP2 = sp2.id
    m.node("SA_Start", "startEvent", "", c[0], YM, SP2)
    m.node("SA_Varianta", "serviceTask", "Calculează și salvează totaluri, varianță, alertă (regulă)", c[1], YM, SP2)
    m.node("SA_AnalizaAI", "serviceTask", "Analiză AI (Groq)", c[2], YM, SP2)
    ai = m.nodes["SA_AnalizaAI"]
    m.node("SA_EroareAI", "boundaryEvent", "Eroare AI", ai.cx, ai.y + ai.h, SP2,
           attrs={"attachedToRef": ai.id}, body=[error_def("AI", "Error_AI")],
           label=("abs", (ai.cx - 70, ai.y + ai.h + 4, 50, 14)))
    m.node("SA_Salveaza", "serviceTask", "Salvează analiza (OK; verifică alerta AI vs. regulă)", c[3], YM, SP2)
    m.node("SA_Esuata", "serviceTask", "Marchează analiza eșuată (Status = Eșuată)", c[3], YM + 120, SP2)
    m.node("SA_Merge", "exclusiveGateway", "", c[4], YM, SP2)
    m.node("SA_End", "endEvent", "", c[5], YM, SP2)
    m.chain("SA_Start", "SA_Varianta", "SA_AnalizaAI", "SA_Salveaza", "SA_Merge", "SA_End")
    m.flow("SA_EroareAI", "SA_Esuata", ss="b", ts="l")
    m.flow("SA_Esuata", "SA_Merge", ts="b")

    m.node("Task_Raport", "serviceTask", "Generează raportul HTML", xs["raport"], YM, P)
    m.node("Send_Raport", "sendTask", "Trimite raportul (email echipă + BCC, Teams)", xs["send"], YM, P)
    m.node("Task_MutaFisier", "serviceTask", "Mută fișierul în Procesate și jurnalizează", xs["muta"], YM, P)
    m.node("End_ImportFinalizat", "endEvent", "Import finalizat", xs["end"], YM, P)

    # top-level flows
    off = YM - sp2.cy
    m.chain("Start_FisierNou", "Task_CitesteFisier", "Gateway_Lizibil")
    m.flow("Gateway_Lizibil", "Task_Referinte", "Da")
    m.flow("Gateway_Lizibil", "Send_NotifEsec", "Nu", ss="b", ts="t")
    m.flow("Send_NotifEsec", "End_ImportEsuat")
    m.chain("Task_Referinte", SP1, "Task_Upsert", "Task_SalveazaErori")
    m.flow("Task_SalveazaErori", SP2, ts=("l", off))
    m.flow(SP2, "Task_Raport", ss=("r", off))
    m.chain("Task_Raport", "Send_Raport", "Task_MutaFisier", "End_ImportFinalizat")

    # external services (collapsed pools above the tasks that call them)
    ref = m.nodes["Task_Referinte"]
    m.participant("Participant_BNR2", "BNR – curs valutar zilnic", ref.cx - 110, 40, 220, 60)
    m.participant("Participant_Groq", "Groq AI – chat completions (gpt-oss-120b)", ai.cx - 140, 40, 280, 60)
    m.message("Task_Referinte", "Participant_BNR2", "GET curs", ref.cx - 15, "left", 0.6)
    m.message("Participant_BNR2", "Task_Referinte", "curs EUR / USD", ref.cx + 15, "right", 0.4)
    m.message("SA_AnalizaAI", "Participant_Groq", "prompt + date CC", ai.cx - 15, "left", 0.6)
    m.message("Participant_Groq", "SA_AnalizaAI", "JSON analiză", ai.cx + 15, "right", 0.4)

    # data stores
    up, er = m.nodes["Task_Upsert"], m.nodes["Task_SalveazaErori"]
    sv, fa = m.nodes["SA_Salveaza"], m.nodes["SA_Esuata"]
    m.node("Store_Nomenclator", "dataStoreReference", "Nomenclator", xs["read"] + 10, ROW0, P, label=("left", 80))
    m.node("Store_Realizat", "dataStoreReference", "Realizat_Lunar", up.cx - 45, ROW0, P, label=("left", 95))
    m.node("Store_Bugete", "dataStoreReference", "Bugete", up.cx + 45, ROW0, P, label=("right", 60))
    m.node("Store_Erori", "dataStoreReference", "Erori_Import", er.cx + 55, ROW0, P, label=("right", 80))
    m.node("Store_Analize1", "dataStoreReference", "Analize_AI", sv.cx, ROW0, P, label=("right", 80))
    m.node("Store_Analize2", "dataStoreReference", "Analize_AI", fa.cx, ROW2, P, label=("right", 80))
    m.data_in("Store_Nomenclator", "Task_Referinte", dx=-35)
    m.data_out("Task_Upsert", "Store_Realizat", dx=-25)
    m.data_out("Task_Upsert", "Store_Bugete", dx=25)
    m.data_out("Task_SalveazaErori", "Store_Erori")
    m.data_out("SA_Salveaza", "Store_Analize1")
    m.data_out("SA_Esuata", "Store_Analize2")

    m.annotation(
        "Annotation_Validare",
        "Apply to each (concurrency 1): rândurile valide merg în varValide; cele invalide și duplicatele "
        "merg în varErori, cu mesaj personalizat (rând, cheie, valoare primită și așteptată).",
        sp1_x + 40, ROW2 - 38, 380, 76, P, target=SP1, target_port=("b", -300),
    )
    m.annotation(
        "Annotation_AI",
        "Scope AI_Try / AI_Catch: calculele se salvează înainte de apel; un eșec al AI nu oprește importul, raportul se trimite oricum.",
        sp2_x + 100, ROW2 - 30, 300, 60, P, target=SP2, target_port=("b", -250),
    )
    return m


def main():
    for name, builder in (("flux1_cerere_achizitie.bpmn", build_flux1), ("flux2_import_analiza.bpmn", build_flux2)):
        path = OUT_DIR / name
        xml = to_ascii(builder().to_xml())
        assert xml.isascii(), f"non-ASCII characters left in {name}"
        path.write_text(xml, encoding="utf-8")
        print(f"wrote {path.relative_to(OUT_DIR.parent)}")


if __name__ == "__main__":
    main()

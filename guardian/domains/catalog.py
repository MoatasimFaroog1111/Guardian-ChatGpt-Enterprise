"""Screaming Architecture catalog: explicit bounded contexts and capabilities."""
DOMAINS = {
 "command_center":["identity","intentions","commands","workflows","approvals","evidence","audit"],
 "agent_os":["planning","delegation","execution","verification","memory","skills","risk"],
 "finance":["accounting","reconciliation","payables","receivables","treasury","tax","audit","reporting"],
 "operations":["capture","vision","counting","reconciliation","devices","erp"],
 "engineering":["repositories","delivery","quality","ci","release","operations"],
 "intelligence":["routing","providers","evaluation","training","registry","multimodal"],
 "investments":["research","forecasting","strategy","risk","approval","execution","accounting"],
 "data_fabric":["canonical","finance","operations","knowledge","events","storage","governance"],
}

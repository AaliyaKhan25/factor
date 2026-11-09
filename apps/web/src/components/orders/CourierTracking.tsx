"use client";

import Link from "next/link";
import { useState } from "react";
import { api, type CourierTracking as Shipment } from "@/lib/api";
import { usePolling } from "@/hooks/usePolling";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import Icon from "@/components/ui/Icon";
import ErrorText from "@/components/ui/ErrorText";

type Connection={id:number;name:string;provider:string;credentials_configured:boolean};
const statuses=["label_created","picked_up","in_transit","out_for_delivery","delivered","exception","returned"];
const label=(s:string)=>s.replaceAll("_"," ").replace(/\b\w/g,c=>c.toUpperCase());

export default function CourierTracking({orderId,tracking,onUpdated}:{orderId:number;tracking:Shipment|null|undefined;onUpdated:()=>void}){
 const {data:connections}=usePolling(()=>api<Connection[]>("/couriers"),30000,"courier-connections");
 const [name,setName]=useState("");const [awb,setAwb]=useState("");const [url,setUrl]=useState("");const [connectionId,setConnectionId]=useState("");const [busy,setBusy]=useState(false);const [error,setError]=useState("");
 async function save(event:React.FormEvent){event.preventDefault();setBusy(true);setError("");try{await api(`/couriers/orders/${orderId}/shipment`,{method:"PUT",body:{courier_name:name,awb,tracking_url:url||null,courier_connection_id:connectionId?Number(connectionId):null}});onUpdated();}catch(e){setError(e instanceof Error?e.message:"Could not save tracking");}finally{setBusy(false);}}
 async function updateStatus(status:string){setBusy(true);setError("");try{await api(`/couriers/orders/${orderId}/status`,{body:{status,detail:"Updated by the seller"}});onUpdated();}catch(e){setError(e instanceof Error?e.message:"Could not update courier status");}finally{setBusy(false);}}
 async function poll(){setBusy(true);setError("");try{await api(`/couriers/orders/${orderId}/poll`);onUpdated();}catch(e){setError(e instanceof Error?e.message:"Courier poll failed");}finally{setBusy(false);}}
 return <Card className="courier-card"><div className="courier-card-head"><span className="courier-icon"><Icon name="truck"/></span><div><h2 className="font-serif text-xl font-bold">Courier tracking</h2><p className="text-xs text-stone-500">Optional. Manual tracking works without a courier connection.</p></div></div><ErrorText message={error}/>{tracking?<><div className="courier-summary"><div><small>Courier</small><strong>{tracking.courier_name}</strong></div><div><small>AWB number</small><strong className="font-mono">{tracking.awb}</strong></div><div><small>Latest update</small><strong>{label(tracking.status)}</strong><small>{new Date(tracking.updated_at).toLocaleString()}</small></div>{tracking.tracking_url&&<a className="courier-track-link" href={tracking.tracking_url} target="_blank" rel="noreferrer">Open tracking <Icon name="arrow" size={14}/></a>}</div><div className="courier-status-actions"><span className="text-xs font-bold text-stone-500">Update status</span><div>{statuses.map(s=><button key={s} disabled={busy||tracking.status===s} className={tracking.status===s?"courier-status-current":""} onClick={()=>updateStatus(s)}>{label(s)}</button>)}</div></div>{tracking.courier_connection_id?<Button variant="secondary" disabled={busy} onClick={poll}><Icon name="refresh"/>Poll courier</Button>:null}</>:<form onSubmit={save} className="courier-form"><label><span>Courier name</span><input value={name} onChange={e=>setName(e.target.value)} placeholder="e.g. Delhivery" required/></label><label><span>AWB number</span><input value={awb} onChange={e=>setAwb(e.target.value)} placeholder="Enter tracking number" required/></label><label><span>Tracking link <small>Optional</small></span><input type="url" value={url} onChange={e=>setUrl(e.target.value)} placeholder="https://…"/></label><label><span>Courier connection <small>Optional</small></span><select value={connectionId} onChange={e=>{setConnectionId(e.target.value);const selected=connections?.find(c=>String(c.id)===e.target.value);if(selected)setName(selected.name);}}><option value="">Manual updates only</option>{(connections??[]).map(c=><option value={c.id} key={c.id}>{c.name} · {c.provider}</option>)}</select></label><div className="courier-form-actions"><Button disabled={busy}>{busy?"Saving…":"Save tracking details"}</Button><Link href="/settings" className="courier-settings-link">Set up a courier <Icon name="arrow" size={13}/></Link></div></form>}<p className="courier-footnote"><Icon name="info" size={14}/> Every courier status is added to this order’s evidence timeline.</p></Card>;
}

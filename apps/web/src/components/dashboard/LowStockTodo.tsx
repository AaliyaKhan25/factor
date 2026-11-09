"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type Dashboard } from "@/lib/api";
import Icon from "@/components/ui/Icon";

export default function LowStockTodo(){
 const [todo,setTodo]=useState<Dashboard["todo"][number]|null>(null);
 useEffect(()=>{let active=true;const load=()=>api<Dashboard>("/dashboard").then(d=>{if(active)setTodo(d.todo.find(item=>item.kind==="inventory")??null);}).catch(()=>{});void load();const id=setInterval(load,5000);return()=>{active=false;clearInterval(id);};},[]);
 if(!todo)return null;
 return <Link href={todo.href} className="attention-item"><span className="attention-icon attention-icon-yellow"><Icon name="box" size={18}/></span><span><strong>{todo.title}</strong><small>{todo.detail}</small></span><Icon name="chevron" size={17}/></Link>;
}

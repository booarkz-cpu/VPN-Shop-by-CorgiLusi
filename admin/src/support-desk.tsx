import React, {useEffect, useRef, useState} from "react";
export function SupportDesk({rows,request,reload}:{rows:any[];request:(p:string,o?:RequestInit)=>Promise<any>;reload:()=>void}){
 const [filter,setFilter]=useState("open"),[selected,setSelected]=useState<any>(null),[reply,setReply]=useState(""),[thread,setThread]=useState<any>(null),[busy,setBusy]=useState(false),[error,setError]=useState("");
 const serial=useRef(0),locked=useRef(false),retry=useRef<{body:string;key:string}|null>(null);
 const visible=rows.filter(x=>filter==="all"||x.status===filter);
 async function load(ticketId:number,more=false){
  const n=++serial.current;setBusy(true);setError("");
  try{const value=await request(`/api/admin/support/tickets/${ticketId}/messages`+(more?`?after=${thread.next_cursor}`:""));if(n===serial.current)setThread(more?{...value,messages:[...thread.messages,...value.messages]}:value)}
  catch(e:any){if(n===serial.current)setError(e.message)}finally{if(n===serial.current)setBusy(false)}
 }
 useEffect(()=>{if(selected)load(selected.id);return()=>{serial.current++}},[selected?.id]);
 function open(ticket:any){serial.current++;setSelected(ticket);setThread(null);setReply("");retry.current=null;setError("")}
 async function send(e:React.FormEvent){
  e.preventDefault();if(locked.current||!reply.trim())return;locked.current=true;setBusy(true);setError("");
  const body=reply.trim(),ticketId=selected.id;if(retry.current?.body!==body)retry.current={body,key:crypto.randomUUID()};
  try{await request(`/api/admin/support/tickets/${ticketId}/reply`,{method:"POST",body:JSON.stringify({reply:body}),headers:{"Idempotency-Key":retry.current!.key}});setReply("");retry.current=null;await load(ticketId);reload()}
  catch(e:any){setError(e.message)}finally{locked.current=false;setBusy(false)}
 }
 return <div className="customer-desk"><div className="card"><h2>Обращения клиентов</h2><p>Ответ появится в кабинете, Mini App и уведомлениях клиента. Новый ответ клиента снова открывает обращение.</p><label>Показать<select value={filter} onChange={e=>setFilter(e.target.value)}><option value="open">Открытые</option><option value="resolved">Решённые</option><option value="all">Все</option></select></label>{error&&<p className="error" role="alert">{error}{selected&&<button type="button" disabled={busy} onClick={()=>load(selected.id)}>Повторить загрузку</button>}</p>}</div>
 {selected?<form className="card" onSubmit={send}><div className="toolbar"><h3>#{selected.id} · {selected.subject}</h3><button type="button" disabled={busy} onClick={()=>open(null)}>К списку</button></div><p>Клиент #{selected.user_id}</p>{thread?<><p>{thread.status==="resolved"?"Решено":"Открыто"}</p><div className="support-messages">{thread.messages.map((m:any)=><div className={`support-message ${m.role}`} key={m.id}><strong>{m.role==="admin"?"Поддержка":"Клиент"}</strong><small>{new Date(m.created_at).toLocaleString()}</small><p>{m.body}</p></div>)}</div>{thread.next_cursor!==null&&<button type="button" disabled={busy} onClick={()=>load(selected.id,true)}>Загрузить следующие сообщения</button>}</>:!error&&<p>Загрузка переписки…</p>}<label>Ответ<textarea required maxLength={10000} value={reply} onChange={e=>setReply(e.target.value)} disabled={busy}/></label><button className="primary" disabled={busy||!thread||!reply.trim()}>{busy?"Отправка…":"Отправить ответ"}</button></form>:<div className="card table-card"><div className="table-wrap"><table><thead><tr><th>№</th><th>Клиент</th><th>Тема</th><th>Статус</th><th/></tr></thead><tbody>{visible.map(x=><tr key={x.id}><td>{x.id}</td><td>{x.user_id}</td><td>{x.subject}</td><td>{x.status==="resolved"?"Решено":"Открыто"}</td><td><button onClick={()=>open(x)}>Открыть</button></td></tr>)}{!visible.length&&<tr><td colSpan={5} className="empty-state">Обращений пока нет</td></tr>}</tbody></table></div></div>}</div>
}

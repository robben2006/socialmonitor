import { useState, useEffect } from "react";

const API_URL = "http://localhost:8000";

function TimelineChart({ data }) {
  if (!data || data.length === 0) return (
    <div style={{ color: "#525252", fontSize: 13, padding: "20px 0" }}>Aucune donnée timeline</div>
  );
  const maxVal = Math.max(...data.map(d => (d.positive||0)+(d.negative||0)+(d.neutral||0)), 1);
  return (
    <div style={{ display:"flex", alignItems:"flex-end", gap:8, paddingTop:8, height:120 }}>
      {data.map((d,i) => {
        const pos = ((d.positive||0)/maxVal)*100;
        const neg = ((d.negative||0)/maxVal)*100;
        const neu = ((d.neutral||0)/maxVal)*100;
        return (
          <div key={i} style={{ flex:1, display:"flex", flexDirection:"column", alignItems:"center", gap:2 }}>
            <div style={{ width:"100%", display:"flex", flexDirection:"column", justifyContent:"flex-end", height:100 }}>
              <div style={{ height:`${pos}px`, background:"#22c55e", borderRadius:"3px 3px 0 0", minHeight:pos>0?2:0 }}/>
              <div style={{ height:`${neu}px`, background:"#525252", minHeight:neu>0?2:0 }}/>
              <div style={{ height:`${neg}px`, background:"#ef4444", borderRadius:"0 0 3px 3px", minHeight:neg>0?2:0 }}/>
            </div>
            <span style={{ fontSize:10, color:"#525252" }}>{d.hour||`H${i}`}</span>
          </div>
        );
      })}
    </div>
  );
}

function SentimentBar({ value }) {
  const pct = Math.abs(value)*100;
  const isNeg = value < 0;
  return (
    <div style={{ display:"flex", alignItems:"center", gap:8, flex:1 }}>
      <div style={{ flex:1, height:6, background:"#1e1e2e", borderRadius:3, overflow:"hidden" }}>
        <div style={{ height:"100%", width:`${pct}%`, background:isNeg?"#ef4444":"#22c55e", borderRadius:3 }}/>
      </div>
      <span style={{ fontSize:11, color:isNeg?"#ef4444":"#22c55e", minWidth:40 }}>
        {value>0?"+":""}{(value*100).toFixed(0)}%
      </span>
    </div>
  );
}

export default function App() {
  const [data, setData] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("overview");
  const [newPost, setNewPost] = useState("");
  const [sending, setSending] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);

  const fetchData = async () => {
    try {
      const [dashRes, timelineRes, postsRes] = await Promise.all([
        fetch(`${API_URL}/api/dashboard`),
        fetch(`${API_URL}/api/timeline`),
        fetch(`${API_URL}/api/posts?limit=10`),
      ]);
      setData(await dashRes.json());
      setTimeline((await timelineRes.json()).timeline || []);
      setPosts((await postsRes.json()).posts || []);
      setLastUpdate(new Date().toLocaleTimeString("fr-FR"));
      setError(null);
    } catch(e) {
      setError("Impossible de joindre l'API. Vérifie que le serveur tourne sur localhost:8000");
    } finally { setLoading(false); }
  };

  const addPost = async () => {
    if (!newPost.trim()) return;
    setSending(true);
    try {
      await fetch(`${API_URL}/api/posts/add`, {
        method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify({ content: newPost }),
      });
      setNewPost("");
      await fetchData();
    } catch(e) { alert("Erreur lors de l'ajout"); }
    finally { setSending(false); }
  };

  const triggerAnalysis = async () => {
    await fetch(`${API_URL}/api/analyze`, { method:"POST" });
    await fetchData();
  };

  useEffect(() => {
    fetchData();
    const iv = setInterval(fetchData, 30000);
    return () => clearInterval(iv);
  }, []);

  const sevColor = { high:"#ef4444", medium:"#f59e0b", low:"#3b82f6" };
  const sentColor = s => s==="positif"?"#22c55e":s==="negatif"?"#ef4444":"#737373";

  if (loading) return <div style={{ minHeight:"100vh", background:"#0a0a0f", display:"flex", alignItems:"center", justifyContent:"center", color:"#818cf8", fontFamily:"monospace" }}>Chargement...</div>;
  if (error) return <div style={{ minHeight:"100vh", background:"#0a0a0f", display:"flex", alignItems:"center", justifyContent:"center", flexDirection:"column", gap:16, padding:32 }}><div style={{ color:"#ef4444", fontFamily:"monospace", textAlign:"center" }}>{error}</div><button onClick={fetchData} style={{ padding:"8px 20px", background:"#818cf8", color:"#fff", border:"none", borderRadius:6, cursor:"pointer", fontFamily:"monospace" }}>Réessayer</button></div>;

  const { summary, subjects, alerts } = data;
  const total = (summary.positive+summary.negative+summary.neutral)||1;

  return (
    <div style={{ minHeight:"100vh", background:"#0a0a0f", color:"#e5e5e5", fontFamily:"monospace" }}>
      <style>{`*{box-sizing:border-box;margin:0;padding:0}.card{background:#0f0f1a;border:1px solid #1e1e3a;border-radius:8px;padding:20px}.lbl{font-size:11px;letter-spacing:2px;color:#525252;text-transform:uppercase;margin-bottom:10px}.nb{padding:6px 16px;border:1px solid #1e1e3a;background:transparent;color:#737373;font-family:monospace;font-size:11px;letter-spacing:1px;cursor:pointer;border-radius:4px;text-transform:uppercase}.nb.act{border-color:#818cf8;color:#818cf8;background:#818cf811}.live{display:inline-block;width:7px;height:7px;border-radius:50%;background:#22c55e;margin-right:6px;animation:pulse 1.5s infinite}@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}`}</style>

      <div style={{ background:"#0f0f1a", borderBottom:"1px solid #1e1e3a", padding:"16px 32px", display:"flex", justifyContent:"space-between", alignItems:"center" }}>
        <div>
          <div style={{ fontSize:16, fontWeight:700 }}>Social<span style={{ color:"#818cf8" }}>Monitor</span>.py</div>
          <div style={{ fontSize:11, color:"#525252", marginTop:3 }}>Tableau de bord analytique</div>
        </div>
        <div style={{ textAlign:"right" }}>
          <div style={{ fontSize:12, color:"#818cf8" }}><span className="live"/>EN DIRECT</div>
          {lastUpdate && <div style={{ fontSize:10, color:"#525252", marginTop:2 }}>Mis à jour à {lastUpdate}</div>}
        </div>
      </div>

      <div style={{ background:"#0f0f1a", borderBottom:"1px solid #1e1e3a", padding:"10px 32px", display:"flex", gap:6, alignItems:"center" }}>
        {["overview","sujets","alertes","posts","ajouter"].map(t => (
          <button key={t} className={`nb ${tab===t?"act":""}`} onClick={()=>setTab(t)}>{t}</button>
        ))}
        <button onClick={triggerAnalysis} style={{ marginLeft:"auto", background:"transparent", color:"#818cf8", border:"1px solid #818cf8", padding:"6px 14px", borderRadius:6, cursor:"pointer", fontFamily:"monospace", fontSize:11 }}>↻ Analyser</button>
      </div>

      <div style={{ padding:"24px 32px", display:"grid", gap:20 }}>
        <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:14 }}>
          {[
            { label:"Posts analysés", value:summary.total_posts, color:"#818cf8" },
            { label:"Sentiment positif", value:`${summary.positive_pct}%`, color:"#22c55e", sub:`${summary.positive} posts` },
            { label:"Sentiment négatif", value:`${summary.negative_pct}%`, color:"#ef4444", sub:`${summary.negative} posts` },
            { label:"Alertes actives", value:summary.alert_count, color:"#f59e0b" },
          ].map((k,i) => (
            <div key={i} className="card">
              <div className="lbl">{k.label}</div>
              <div style={{ fontSize:32, fontWeight:800, color:k.color, lineHeight:1 }}>{k.value}</div>
              {k.sub && <div style={{ fontSize:11, color:"#525252", marginTop:6 }}>{k.sub}</div>}
            </div>
          ))}
        </div>

        {tab==="overview" && (
          <div style={{ display:"grid", gridTemplateColumns:"2fr 1fr", gap:20 }}>
            <div className="card">
              <div className="lbl">Évolution du sentiment</div>
              <TimelineChart data={timeline}/>
              <div style={{ display:"flex", gap:16, marginTop:12 }}>
                {[["#22c55e","Positif"],["#525252","Neutre"],["#ef4444","Négatif"]].map(([c,l])=>(
                  <div key={l} style={{ display:"flex", alignItems:"center", gap:6, fontSize:11, color:"#737373" }}>
                    <div style={{ width:8, height:8, borderRadius:2, background:c }}/>{l}
                  </div>
                ))}
              </div>
            </div>
            <div className="card">
              <div className="lbl">Sujet dominant</div>
              <div style={{ color:"#818cf8", fontSize:16, fontWeight:700, marginBottom:16 }}>{summary.top_subject}</div>
              <div className="lbl">Répartition</div>
              {[["Positif",summary.positive,"#22c55e"],["Négatif",summary.negative,"#ef4444"],["Neutre",summary.neutral,"#525252"]].map(([l,v,c])=>(
                <div key={l} style={{ display:"flex", alignItems:"center", gap:10, marginBottom:8 }}>
                  <span style={{ fontSize:12, color:"#737373", minWidth:52 }}>{l}</span>
                  <div style={{ flex:1, height:6, background:"#1e1e2e", borderRadius:3 }}>
                    <div style={{ height:"100%", width:`${(v/total)*100}%`, background:c, borderRadius:3 }}/>
                  </div>
                  <span style={{ fontSize:11, color:c, minWidth:28 }}>{Math.round((v/total)*100)}%</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {(tab==="overview"||tab==="sujets") && (
          <div className="card">
            <div className="lbl">Score de sentiment par sujet</div>
            {subjects.map((s,i)=>(
              <div key={i} style={{ display:"flex", alignItems:"center", gap:12, marginBottom:12 }}>
                <span style={{ fontSize:13, minWidth:200, color:"#d4d4d4" }}>{s.name}</span>
                <span style={{ fontSize:11, color:"#525252", minWidth:30 }}>{s.count}</span>
                <SentimentBar value={s.sentiment}/>
              </div>
            ))}
          </div>
        )}

        {(tab==="alertes"||tab==="overview") && alerts.length>0 && (
          <div className="card">
            <div className="lbl">Alertes intelligentes</div>
            {alerts.map(a=>(
              <div key={a.id} style={{ display:"flex", gap:14, padding:12, borderRadius:6, marginBottom:8, background:"#0a0a0f", borderLeft:`3px solid ${sevColor[a.severity]||"#525252"}` }}>
                <div style={{ flex:1 }}>
                  <div style={{ fontSize:10, padding:"2px 6px", borderRadius:3, display:"inline-block", marginBottom:4, background:(sevColor[a.severity]||"#525252")+"22", color:sevColor[a.severity]||"#525252" }}>
                    {a.severity==="high"?"CRITIQUE":a.severity==="medium"?"MOYEN":"FAIBLE"}
                  </div>
                  <div style={{ fontSize:13, color:"#d4d4d4", marginBottom:4 }}>{a.text}</div>
                  <div style={{ fontSize:10, color:"#525252" }}>{a.count} mentions · {a.subject}</div>
                </div>
              </div>
            ))}
          </div>
        )}
        {tab==="alertes"&&alerts.length===0&&<div className="card" style={{ color:"#525252", fontSize:13 }}>Aucune alerte active.</div>}

        {tab==="posts" && (
          <div className="card">
            <div className="lbl">Derniers posts analysés</div>
            {posts.map((p,i)=>(
              <div key={i} style={{ padding:12, borderRadius:6, marginBottom:8, border:"1px solid #1e1e3a", background:"#0a0a0f" }}>
                <div style={{ fontSize:13, color:"#d4d4d4", fontStyle:"italic", marginBottom:8, lineHeight:1.5 }}>« {p.content} »</div>
                <div style={{ display:"flex", gap:6, flexWrap:"wrap" }}>
                  <span style={{ fontSize:10, padding:"2px 8px", borderRadius:3, background:"#818cf811", color:"#818cf8" }}>{p.subject}</span>
                  <span style={{ fontSize:10, padding:"2px 8px", borderRadius:3, color:sentColor(p.sentiment_label), border:`1px solid ${sentColor(p.sentiment_label)}44` }}>
                    {p.sentiment_label} ({p.sentiment_score>0?"+":""}{p.sentiment_score})
                  </span>
                  <span style={{ fontSize:10, padding:"2px 8px", borderRadius:3, background:"#1e1e2e", color:"#525252" }}>{p.source}</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {tab==="ajouter" && (
          <div className="card">
            <div className="lbl">Ajouter un post manuellement</div>
            <div style={{ fontSize:12, color:"#525252", marginBottom:16 }}>Simule un post étudiant — analysé immédiatement.</div>
            <div style={{ display:"flex", gap:10 }}>
              <input type="text" value={newPost} onChange={e=>setNewPost(e.target.value)} onKeyDown={e=>e.key==="Enter"&&addPost()}
                placeholder="Ex: Le Wi-Fi ne fonctionne plus à la bibliothèque..."
                style={{ flex:1, background:"#0a0a0f", border:"1px solid #1e1e3a", color:"#e5e5e5", padding:"8px 12px", borderRadius:6, fontFamily:"monospace", fontSize:13, outline:"none" }}/>
              <button onClick={addPost} disabled={sending} style={{ background:"#818cf8", color:"#fff", border:"none", padding:"8px 16px", borderRadius:6, cursor:"pointer", fontFamily:"monospace", fontSize:12 }}>
                {sending?"Envoi...":"Analyser →"}
              </button>
            </div>
            <div style={{ marginTop:20 }}>
              <div className="lbl">Exemples à tester</div>
              {[
                "La connexion Wi-Fi est catastrophique aujourd'hui !",
                "Excellent cours de mathématiques ce matin, merci professeur !",
                "Les résultats du partiel ne sont toujours pas publiés...",
                "Super organisation pour la journée d'intégration !",
                "Le secrétariat ne répond jamais à nos emails",
              ].map((ex,i)=>(
                <div key={i} onClick={()=>setNewPost(ex)}
                  style={{ padding:"8px 12px", margin:"4px 0", borderRadius:4, border:"1px solid #1e1e3a", fontSize:12, color:"#737373", cursor:"pointer" }}>
                  {ex}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
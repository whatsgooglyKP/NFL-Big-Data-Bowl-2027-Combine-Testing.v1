"""Exploratory tests of candidate Combine->NFL metrics. Run after profile.py."""
import pandas as pd, numpy as np
from scipy import stats
D='/workspace/bdb2027/data/'; O='/workspace/bdb2027/out/'
log=open(O+'explore.txt','w')
def P(*a):
    s=' '.join(str(x) for x in a); print(s); log.write(s+'\n')
pl=pd.read_csv(D+'players.csv').set_index('nfl_id')
pl['pick']=pl.draft_overall_pick.fillna(260)
cs=pd.read_csv(D+'player_career_successes.csv').set_index('nfl_id')
pp=pd.read_parquet(O+'player_play.parquet')
POS={'WR':['WR'],'CB':['CB'],'S':['FS','SS']}
ids=pl.index[pl.nfl_position.isin(['WR','CB','FS','SS'])]
# ---------- combine features (signed accel from ds/dt) ----------
ct=pd.read_csv(D+'combine_tracking.csv'); ct=ct[(ct.entity_type=='PLAYER')&ct.nfl_id.isin(ids)].sort_values(['event_id','time'])
ct['ds']=ct.groupby('event_id').s.diff()*10
def att(g):
    s=g.s.values; ds=g.ds.values; i=np.nanargmax(s); m=s[i]
    t90=np.argmax(s>=0.9*m)/10
    return pd.Series({'max_s':m,'t90':t90,'brake':-np.nanmin(ds),'accel':np.nanmax(ds)})
fa=ct.groupby(['nfl_id','drill_type','drill_name','event_id']).apply(att).reset_index()
f40=fa[fa.drill_type=='FORTY_YARD_DASH'].groupby('nfl_id').agg(c_top=('max_s','max'),c_t90=('t90','min'))
agil=fa[fa.drill_type.isin(['THREE_CONE_DRILL','SHORT_SHUTTLE'])].groupby('nfl_id').agg(c_brake_agil=('brake','max'))
skill=fa[fa.drill_type.str.startswith('SKILL')].groupby('nfl_id').agg(c_brake_skill=('brake','median'),c_reaccel_skill=('accel','median'),c_skill_cv=('max_s',lambda x:x.std()/x.mean()))
C=f40.join(agil,how='outer').join(skill,how='outer')
# ---------- game features (cohort WR/CB/S only) ----------
parts=[]
for yr in [2023,2024,2025]:
    for ch in pd.read_csv(D+f'game_tracking_{yr}.csv',usecols=['game_id','play_id','nfl_id','time','s'],chunksize=5_000_000):
        ch=ch[ch.nfl_id.isin(ids)].sort_values(['game_id','play_id','nfl_id','time'])
        ch['ds']=ch.groupby(['game_id','play_id','nfl_id']).s.diff()*10
        ch.loc[ch.ds.abs()>12,'ds']=np.nan  # glitch guard
        parts.append(ch.groupby(['game_id','play_id','nfl_id']).agg(max_s=('s','max'),brake=('ds','min')).reset_index())
G=pd.concat(parts).groupby(['game_id','play_id','nfl_id']).agg(max_s=('max_s','max'),brake=('brake','min')).reset_index()
G['brake']=-G.brake
G=G.merge(pp[['game_id','play_id','nfl_id','quarter','route_ran','separation_at_pass_forward','target','lined_up_position','tackle','assist','yards_after_catch','expected_yards_after_catch']],on=['game_id','play_id','nfl_id'],how='left')
G.to_parquet(O+'game_dbwr_play.parquet')
DEEP={'GO','POST','CORNER','WHEEL'}; BREAK={'HITCH','OUT','IN','SLANT','CROSS'}
def agg_player(g):
    deep=g[g.route_ran.isin(DEEP)]; brk=g[g.route_ran.isin(BREAK)]
    r={'plays':len(g),'g_p95':g.max_s.quantile(.95),'g_deep_p90':deep.max_s.quantile(.9) if len(deep)>=20 else np.nan,
       'g_brake_brk':brk.brake.median() if len(brk)>=20 else np.nan,
       'sep_brk':brk.separation_at_pass_forward.mean() if brk.separation_at_pass_forward.notna().sum()>=20 else np.nan,
       'sep_deep':deep.separation_at_pass_forward.mean() if deep.separation_at_pass_forward.notna().sum()>=20 else np.nan,
       'q4_ret':g[g.quarter==4].max_s.quantile(.9)/g[g.quarter==1].max_s.quantile(.9) if min((g.quarter==4).sum(),(g.quarter==1).sum())>=30 else np.nan,
       'tk_rate':(g.tackle.fillna(0).astype(float)+g.assist.fillna(0).astype(float)).mean()}
    return pd.Series(r)
Gp=G.groupby('nfl_id').apply(agg_player)
M=Gp.join(C).join(pl[['nfl_position','pick']]).join(cs)
M['realization']=M.g_deep_p90/M.c_top
M['start_rate']=M.career_games_started/M.career_games_active.replace(0,np.nan)
M.to_parquet(O+'explore_player.parquet')
def test(name,x,y,pos,min_plays=100):
    d=M[M.nfl_position.isin(POS[pos])&(M.plays>=min_plays)][[x,y,'pick']].dropna()
    if len(d)<8: P(f'{name:38s} {pos:3s} n={len(d)} too thin'); return
    r,p=stats.spearmanr(d[x],d[y])
    # partial: residualize on log pick
    lp=np.log(d.pick); rx=d[x]-np.poly1d(np.polyfit(lp,d[x],1))(lp); ry=d[y]-np.poly1d(np.polyfit(lp,d[y],1))(lp)
    pr,pp_=stats.spearmanr(rx,ry)
    P(f'{name:38s} {pos:3s} n={len(d):3d} rho={r:+.2f} p={p:.3f} | partial(pick) rho={pr:+.2f} p={pp_:.3f}')
P('== Candidate tests (Spearman; partial controls for log draft pick) ==')
for pos in ['WR','CB','S']:
    test('A1 combine top -> game deep p90 speed','c_top','g_deep_p90' if pos=='WR' else 'g_p95',pos)
    test('A2 realization -> start rate','realization','start_rate',pos)
    test('A3 combine top -> start rate','c_top','start_rate',pos)
    test('B1 agility brake -> game brake (breaks)','c_brake_agil','g_brake_brk',pos)
    test('B2 skill-drill brake -> game brake','c_brake_skill','g_brake_brk',pos)
    test('B3 skill brake -> separation on breaks','c_brake_skill','sep_brk',pos)
    test('B4 agility brake -> separation on breaks','c_brake_agil','sep_brk',pos)
    test('B5 game brake -> separation on breaks','g_brake_brk','sep_brk',pos)
    test('C1 40 burst t90 -> sep deep','c_t90','sep_deep',pos)
    test('D1 skill-drill CV -> Q4 retention','c_skill_cv','q4_ret',pos)
    test('D2 combine top -> Q4 retention','c_top','q4_ret',pos)
    test('E1 skill brake -> tackle rate','c_brake_skill','tk_rate',pos)
    test('E2 skill reaccel -> start rate','c_reaccel_skill','start_rate',pos)
P('\nCoverage of features by pos (non-null counts, plays>=100):')
P(M[M.plays>=100].groupby('nfl_position')[['c_top','c_brake_agil','c_brake_skill','g_deep_p90','g_brake_brk','sep_brk','q4_ret','realization']].count().to_string())
P('\nDescriptives (median):'); P(M[M.plays>=100].groupby('nfl_position')[['c_top','realization','c_brake_skill','g_brake_brk','sep_brk','q4_ret']].median().round(3).to_string())

# ---------- round 2: DB coverage-context realization, WR outcomes, CB speed tax ----------
P('\n== Round 2 ==')
P('coverage_assignment values:', G.merge(pp[['game_id','play_id','nfl_id','coverage_assignment']],on=['game_id','play_id','nfl_id']).coverage_assignment.value_counts().head(12).to_dict())
G2=G.merge(pp[['game_id','play_id','nfl_id','coverage_assignment','pass_result']],on=['game_id','play_id','nfl_id'],how='left')
db=G2[G2.coverage_assignment.notna()]
deepdb=db[db.coverage_assignment.str.contains('DEEP|MAN',na=False)]
v=deepdb.groupby('nfl_id').max_s.agg(lambda x:x.quantile(.9) if len(x)>=30 else np.nan).rename('g_cov_p90')
M=M.join(v); M['realization_db']=M.g_cov_p90/M.c_top
wr=G2[G2.route_ran.notna()]
y=wr.assign(yoe=wr.yards_after_catch-wr.expected_yards_after_catch).groupby('nfl_id').agg(yac_oe=('yoe','mean'),tgt_rate=('target',lambda x:x.fillna(False).astype(bool).mean()))
M=M.join(y)
M['snap_share']=(M.career_offensive_snaps+M.career_defensive_snaps)/M.career_games_active.replace(0,np.nan)
M['real_resid']=np.nan
for pos in ['WR','CB','S']:
    sub=M.nfl_position.isin(POS[pos])&M.c_top.notna()
    col='g_deep_p90' if pos=='WR' else 'g_cov_p90'
    d=M[sub&M[col].notna()]
    if len(d)>8:
        fit=np.poly1d(np.polyfit(d.c_top,d[col],1)); M.loc[d.index,'real_resid']=d[col]-fit(d.c_top)
        P(f'{pos}: expected game speed = {fit[1]:.3f}*combine_top + {fit[0]:.2f}; resid SD={M.loc[d.index,"real_resid"].std():.2f} yd/s')
for pos in ['WR','CB','S']:
    test('F1 combine top -> game cov/deep p90','c_top','g_deep_p90' if pos=='WR' else 'g_cov_p90',pos)
    test('F2 speed over expected -> start rate','real_resid','start_rate',pos)
    test('F3 speed over expected -> snaps/game','real_resid','snap_share',pos)
    test('F4 combine top -> snaps/game','c_top','snap_share',pos)
    test('F5 combine top -> start rate (speed tax)','c_top','start_rate',pos)
for pos in ['WR']:
    test('F6 speed over expected -> sep deep','real_resid','sep_deep',pos)
    test('F7 speed over expected -> YAC over exp','real_resid','yac_oe',pos)
    test('F8 speed over expected -> target rate','real_resid','tgt_rate',pos)
    test('F9 combine top -> sep deep','c_top','sep_deep',pos)
# stability: split-half (odd/even game) game deep p90
for pos,col,src in [('WR','route_ran',wr[wr.route_ran.isin(DEEP)]),('CB/S','cov',deepdb)]:
    src=src.assign(h=src.game_id%2)
    h=src.groupby(['nfl_id','h']).max_s.agg(lambda x:x.quantile(.9) if len(x)>=15 else np.nan).unstack()
    h=h.dropna(); P(f'split-half stability {pos} p90 game speed: n={len(h)} r={h[0].corr(h[1]):.2f}')
M.to_parquet(O+'explore_player.parquet')

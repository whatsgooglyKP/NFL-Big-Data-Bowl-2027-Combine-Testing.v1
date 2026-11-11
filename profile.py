"""Profile BDB 2027 data. Writes out/*.parquet and out/profile.txt"""
import pandas as pd, numpy as np, os
D='/workspace/bdb2027/data/'; O='/workspace/bdb2027/out/'
log=open(O+'profile.txt','w')
def P(*a):
    s=' '.join(str(x) for x in a); print(s); log.write(s+'\n')
# inventory + schemas of small tables
for f in sorted(os.listdir(D)):
    P(f'## {f}  {os.path.getsize(D+f)/1e6:.1f} MB')
for f in ['players','combine_results','player_career_successes','games']:
    df=pd.read_csv(D+f+'.csv'); P(f'\n### {f} rows={len(df)}'); P(df.dtypes.to_string()); P(df.iloc[0].to_string())
    P('null share:\n'+df.isna().mean().round(3).to_string())
# game tracking -> play-level per player (chunked)
rows=0; parts=[]
for yr in [2023,2024,2025]:
    for ch in pd.read_csv(D+f'game_tracking_{yr}.csv',usecols=['game_id','play_id','nfl_id','s','a','event'],chunksize=5_000_000):
        rows+=len(ch)
        g=ch.groupby(['game_id','play_id','nfl_id']).agg(max_s=('s','max'),max_a=('a','max'),n=('s','size')).reset_index()
        parts.append(g)
    P(f'game_tracking_{yr}: cumulative frames {rows}')
gp=pd.concat(parts).groupby(['game_id','play_id','nfl_id']).agg(max_s=('max_s','max'),max_a=('max_a','max'),n=('n','sum')).reset_index()
gp.to_parquet(O+'game_play_player.parquet'); P('play-player rows',len(gp))
pp=pd.read_csv(D+'player_play.csv'); P(f'\n### player_play rows={len(pp)} cols={pp.shape[1]}'); P(pp.dtypes.to_string())
P('lined_up_position:\n'+pp.lined_up_position.value_counts().to_string())
P('route_ran:\n'+pp.route_ran.value_counts().head(20).to_string())
pp.to_parquet(O+'player_play.parquet')
# combine tracking per attempt
ct=pd.read_csv(D+'combine_tracking.csv'); ct=ct[ct.entity_type=='PLAYER']
ca=ct.groupby(['nfl_id','drill_type','drill_name','event_id']).agg(max_s=('s','max'),max_a=('a','max'),min_a=('a','min'),n=('s','size')).reset_index()
ca.to_parquet(O+'combine_attempt.parquet'); P('combine attempts',len(ca))
# matched counts
pl=pd.read_csv(D+'players.csv')
pos=pl.set_index('nfl_id').nfl_position
cd=ca.groupby(['nfl_id','drill_type']).size().unstack(fill_value=0)>0
snaps=gp.groupby('nfl_id').size()
t=pd.DataFrame({'pos':pos,'snaps':snaps}).join(cd).fillna({'snaps':0})
for c in cd.columns: t[c]=t[c].fillna(False).astype(bool)
t['has_game']=t.snaps>=50
P('\nPer position: players, with 40yd tracking, 3cone, shuttle, game>=50 plays, 40+game, snaps median')
P(t.groupby('pos').agg(n=('snaps','size'),f40=('FORTY_YARD_DASH','sum'),cone=('THREE_CONE_DRILL','sum'),shut=('SHORT_SHUTTLE','sum'),game=('has_game','sum'),
   f40_game=('has_game',lambda x:(x&t.loc[x.index,'FORTY_YARD_DASH']).sum()),med_plays=('snaps','median'),p90_plays=('snaps',lambda x:x.quantile(.9))).to_string())
t.to_parquet(O+'player_coverage.parquet')
# speed sanity check
cm=ca[ca.drill_type=='FORTY_YARD_DASH'].groupby('nfl_id').max_s.max().rename('combine_max')
gm=gp.groupby('nfl_id').max_s.agg(game_max='max',game_p95=lambda x:x.quantile(.95),plays='size')
m=pd.concat([cm,gm],axis=1,join='inner').join(pos); m=m[m.plays>=50]
P('\nSpeed sanity (yd/s; x2.045 = mph). players with 40 tracking & >=50 plays')
for p_,g in m.groupby('nfl_position'):
    if len(g)<5: continue
    P(f'{p_:4s} n={len(g):3d} combine_max={g.combine_max.mean():.2f} game_max={g.game_max.mean():.2f} game_p95={g.game_p95.mean():.2f} '
      f'r(max)={g.combine_max.corr(g.game_max):.2f} r(p95)={g.combine_max.corr(g.game_p95):.2f} rho(max)={g.combine_max.corr(g.game_max,method="spearman"):.2f} realization={(g.game_max/g.combine_max).mean():.3f}')
m.to_parquet(O+'speed_match.parquet')

import React from 'react';

const StraddleCard = ({entry}) => {
  const {strike, call, put, iv_call, iv_put, oi_call, oi_put, oi_change_call, oi_change_put, volume_call, volume_put} = entry || {};

  const pct = (val, total) => (total ? Math.round((val/total)*100) : 0);

  const total_oi = (oi_call || 0) + (oi_put || 0);

  return (
    <div style={{border:'1px solid #ddd', padding:12, borderRadius:6, marginBottom:8, display:'flex', alignItems:'center', justifyContent:'space-between'}}>
      <div style={{width:160}}>
        <div style={{fontWeight:700}}>{strike}</div>
        <div style={{fontSize:12, color:'#666'}}>OI C:{oi_call || 0} / P:{oi_put || 0}</div>
      </div>

      <div style={{flex:1, paddingLeft:12, paddingRight:12}}>
        <div style={{display:'flex', alignItems:'center'}}>
          <div style={{flex:1}}>
            <div style={{height:8, background:'#eee', borderRadius:4, overflow:'hidden'}}>
              <div style={{width:`${pct(oi_call,total_oi)}%`, height:'100%', background:'#2b8be6'}}/>
              <div style={{width:`${pct(oi_put,total_oi)}%`, height:'100%', background:'#e62b2b', marginLeft:-pct(oi_put,total_oi)+'%'}}/>
            </div>
          </div>
          <div style={{width:120, textAlign:'right', fontSize:12}}>
            <div>IV C:{iv_call ?? '-'} P:{iv_put ?? '-'}</div>
            <div>Vol C:{volume_call ?? '-'} P:{volume_put ?? '-'}</div>
          </div>
        </div>
      </div>

      <div style={{width:180, textAlign:'right'}}>
        <div style={{fontSize:12}}>ΔOI C:{oi_change_call ?? 0}</div>
        <div style={{fontSize:12}}>ΔOI P:{oi_change_put ?? 0}</div>
      </div>
    </div>
  );
};

export default StraddleCard;

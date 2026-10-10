/* Read-only guest-state observer for a pinned DOSBox-X normal CPU core.
 * No original instruction, register, memory, timer or input byte is replaced.
 * Optional key events enter through DOSBox's keyboard controller. */
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <chrono>
#include "keyboard.h"
#include "hardware.h"

static FILE *sr_trace=nullptr;
static bool sr_checked=false;
static uint16_t sr_cs=0, sr_ds=0, sr_bp=0;
static unsigned sr_attempt=0, sr_ticks=0, sr_sessions=0;
static bool sr_starting=false,sr_in_tick=false;
static double sr_deadline=0;
static unsigned sr_shot_tick=0;
static unsigned sr_max_sessions=1;
static const char *sr_path=nullptr;
static bool sr_keyboard=false;
static bool sr_graphics=false,sr_gfx_pending=false;
static bool sr_gallery=false;
static bool sr_audio=false;
static bool sr_hud=false,sr_hud_pending=false;
static bool sr_response=false,sr_menus=false;
static unsigned sr_menu_capture=0,sr_main_wait=0,sr_settings_wait=0,sr_help_wait=0,sr_road_wait=0;
static double sr_wall_ms(){static const auto origin=std::chrono::steady_clock::now();return std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-origin).count();}
static unsigned sr_hud_count=0,sr_hud_id=0,sr_hud_attempt=0;
static unsigned sr_audio_irq=0,sr_audio_start=0,sr_audio_score=0;
static unsigned sr_gfx_count=0,sr_gfx_id=0,sr_gfx_attempt=0,sr_gfx_destination=0;
static unsigned sr_menu_stage=0;
static int sr_policy_direction=0;
static unsigned sr_pause_ip=0,sr_pause_mask=0,sr_pause_timer=0;
static void sr_key(Bitu v){KBD_KEYS key=KBD_KEYS(v>>1);bool down=v&1;KEYBOARD_AddKey(key,down);
 if(sr_trace){fprintf(sr_trace,"{\"kind\":\"hardware_key\",\"ms\":%.6f,\"attempt\":%u,\"key\":%u,\"down\":%s,\"host_ms\":%.6f}\n",double(PIC_FullIndex()),sr_attempt,unsigned(key),down?"true":"false",sr_wall_ms());fflush(sr_trace);}}
static void sr_schedule(KBD_KEYS key,bool down,double delay){PIC_AddEvent(sr_key,delay,(unsigned(key)<<1)|unsigned(down));}
static void sr_press(KBD_KEYS key,double start,double duration=50){sr_schedule(key,true,start);sr_schedule(key,false,start+duration);}


static uint16_t sr_word(unsigned o) {return mem_readw((PhysPt(sr_ds)<<4)+(o&65535));}
static uint32_t sr_dword(unsigned o) {return mem_readd((PhysPt(sr_ds)<<4)+(o&65535));}
static unsigned sr_mask() {unsigned m=0;for(unsigned i=0;i<11;i++)if(mem_readb((PhysPt(sr_ds)<<4)+0xbd2+i)&128)m|=1u<<i;return m;}
struct SrField {const char *name;unsigned offset,width;bool sign;};
static const SrField sr_globals[]={
 {"forward",0x9618,4,false},{"lateral",0xaf1c,2,false},{"height",0xaf2c,2,false},
 {"speed",0x54ac,4,false},{"steering",0x4568,2,true},{"vertical_speed",0x9336,2,true},
 {"drift",0x5496,2,true},{"speed_delta",0xaf2e,4,false},{"assist_flag",0x455a,2,false},
 {"fuel",0x5494,2,false},{"oxygen",0xb13c,2,false},{"exit_state",0x456e,2,false},
 {"crash_ticks",0x456a,2,false},{"end_ticks",0x4558,2,false},{"sound_tick",0xaf38,2,false}};
static const SrField sr_locals[]={
 {"tick_counter",2,2,false},{"assist_used",6,2,false},{"jumping",8,2,false},
 {"jump_height",10,2,false},{"grounded",12,2,false},{"surface8",14,2,false},
 {"surface2",16,2,false},{"edge_distance",24,2,false},{"previous_target_height",28,2,false}};
static void sr_log(const char *kind,bool state=true) {
 fprintf(sr_trace,"{\"kind\":\"%s\",\"ms\":%.6f,\"attempt\":%u,\"tick\":%u,\"cs\":%u,\"ds\":%u,\"bp\":%u,\"ip\":%u,\"ax\":%u,\"timer\":%u,\"mode\":%u,\"mask\":%u,\"throttle\":%d,\"direction\":%d,\"jump\":%u,\"config\":[%u,%u,%u,%u,%u],\"selected\":%u",
 kind,double(PIC_FullIndex()),sr_attempt,sr_ticks,sr_cs,sr_ds,sr_bp,unsigned(reg_eip),unsigned(reg_ax),
 sr_word(0x1600),sr_word(0x95f6),sr_mask(),int(int16_t(sr_word(0x9330))),int(int16_t(sr_word(0x95f4))),
 sr_word(0x547a),sr_word(0x4562),sr_word(0x54a2),sr_word(0x4566),sr_word(0x41c0),sr_word(0x4570),sr_word(0x9332));
 if(sr_response)fprintf(sr_trace,",\"host_ms\":%.6f",sr_wall_ms());
 fprintf(sr_trace,",\"audio\":[%u,%u],\"saved_timer\":%u,\"blink\":%u",sr_word(0x451a),sr_word(0xcb6),sr_word(sr_bp-4),sr_word(0xaf1e));
 fprintf(sr_trace,",\"arg0\":%u,\"arg1\":%u,\"arg2\":%u",sr_word(reg_sp+2),sr_word(reg_sp+4),sr_word(reg_sp+6));
 if(!state){fputs(",\"completed\":[",sr_trace);for(unsigned i=0;i<30;i++)fprintf(sr_trace,"%s%u",i?",":"",sr_word(0x451c+2*i));fputc(']',sr_trace);}
 if(state&&sr_bp){fputs(",\"state\":{",sr_trace);bool comma=false;
 for(const auto &f:sr_globals){if(comma)fputc(',',sr_trace);comma=true;long long v=f.width==4?sr_dword(f.offset):sr_word(f.offset);if(f.sign)v=int16_t(v);fprintf(sr_trace,"\"%s\":%lld",f.name,v);}
 for(const auto &f:sr_locals)fprintf(sr_trace,",\"%s\":%u",f.name,sr_word(sr_bp-f.offset));
 fputc('}',sr_trace);}
 fputs("}\n",sr_trace);fflush(sr_trace);
}
static void sr_dump(const char *suffix,unsigned offset,unsigned length) {
 char p[4096];snprintf(p,sizeof(p),"%s.attempt-%u.%s",sr_path,sr_attempt,suffix);
 FILE *f=fopen(p,"wb");if(!f)return;
 for(unsigned i=0;i<length;i++)fputc(mem_readb((PhysPt(sr_ds)<<4)+offset+i),f);fclose(f);
}
static void sr_gfx_dump(const char *suffix,PhysPt address,unsigned length,bool per_attempt=false){
 char path[4096];snprintf(path,sizeof(path),"%s.%s-%u.%s",sr_path,per_attempt?"graphics-attempt":"render",per_attempt?sr_attempt:sr_gfx_id,suffix);
 FILE *f=fopen(path,"wb");if(!f){perror(path);exit(2);}
 for(unsigned i=0;i<length;i++)fputc(mem_readb(address+i),f);fclose(f);
}
static void sr_hud_dump(const char *suffix,PhysPt address,unsigned length){
 char path[4096];snprintf(path,sizeof(path),"%s.hud-%u.%s",sr_path,sr_hud_id,suffix);
 FILE *f=fopen(path,"wb");if(!f){perror(path);exit(2);}
 for(unsigned i=0;i<length;i++)fputc(mem_readb(address+i),f);fclose(f);
}
static void sr_hud_log(const char *kind){
 sr_log(kind);
 fprintf(sr_trace,"{\"kind\":\"hud_cache\",\"id\":%u,\"stage\":\"%s\",\"values\":[%u,%u,%u,%u,%u,%u]}\n",sr_hud_id,kind,
 sr_word(0x41be),sr_word(0x456c),sr_word(0x960c),sr_word(0x455c),sr_word(0xaf20),sr_word(0xaf1e));fflush(sr_trace);
}
static void sr_menu_wait(){
 unsigned caller=sr_word(reg_sp),focus=0;const char *name=nullptr;
 if(caller==0x4fe1){name="main";focus=reg_si;}
 else if(caller==0x4cdf){name="settings";focus=sr_word(reg_bp-2);}
 else if(caller==0x4e07){name="help";focus=sr_help_wait;}
 else if(caller==0x52e4){name="roads";focus=sr_word(0x9332);}
 if(!name)return;
 sr_menu_capture++;char path[4096];snprintf(path,sizeof(path),"%s.menu-%u.bin",sr_path,sr_menu_capture);
 FILE *f=fopen(path,"wb");if(!f){perror(path);exit(2);}for(unsigned i=0;i<64000;i++)fputc(mem_readb(0xa0000+i),f);fclose(f);
 snprintf(path,sizeof(path),"%s.menu-%u.palette.bin",sr_path,sr_menu_capture);f=fopen(path,"wb");if(!f){perror(path);exit(2);}for(unsigned i=0;i<768;i++)fputc(mem_readb((PhysPt(sr_ds)<<4)+0x5174+i),f);fclose(f);
 fprintf(sr_trace,"{\"kind\":\"menu_capture\",\"id\":%u,\"menu\":\"%s\",\"focus\":%u,\"caller\":%u,\"input_mode\":%u,\"music_mode\":%u,\"ms\":%.6f}\n",sr_menu_capture,name,focus,caller,sr_word(0x4518),sr_word(0x451a),double(PIC_FullIndex()));fflush(sr_trace);CaptureState|=CAPTURE_IMAGE;
 if(caller==0x4fe1){static const KBD_KEYS keys[]={KBD_down,KBD_enter,KBD_down,KBD_enter,KBD_up,KBD_up,KBD_enter};if(sr_main_wait<7)sr_press(keys[sr_main_wait++],100,30);}
 else if(caller==0x4cdf){static const KBD_KEYS keys[]={KBD_right,KBD_right,KBD_right,KBD_right,KBD_enter,KBD_left,KBD_enter,KBD_esc};if(sr_settings_wait<8)sr_press(keys[sr_settings_wait++],100,30);}
 else if(caller==0x4e07)sr_press(sr_help_wait++?KBD_esc:KBD_enter,100,30);
 else {if(sr_road_wait<29)sr_press(KBD_down,100,30);else sr_press(KBD_enter,100,30);sr_road_wait++;}
}
static void SkyRoadsProbe() {
 if(!sr_checked){sr_checked=true;sr_path=getenv("SKYROADS_TRACE");if(!sr_path)return;
 sr_keyboard=getenv("SKYROADS_KEYBOARD")!=nullptr;
 sr_graphics=getenv("SKYROADS_GRAPHICS")!=nullptr;
 sr_gallery=getenv("SKYROADS_GALLERY")!=nullptr;
 sr_audio=getenv("SKYROADS_AUDIO")!=nullptr;
 sr_hud=getenv("SKYROADS_HUD")!=nullptr;
 sr_response=getenv("SKYROADS_RESPONSE")!=nullptr;sr_menus=getenv("SKYROADS_MENUS")!=nullptr;
 sr_trace=fopen(sr_path,"w");if(!sr_trace){perror("SKYROADS_TRACE");exit(2);}
 const char *limit=getenv("SKYROADS_MAX_MS");sr_deadline=limit?atof(limit):180000;
 const char *sessions=getenv("SKYROADS_MAX_SESSIONS");if(sessions)sr_max_sessions=atoi(sessions);
 fputs("{\"kind\":\"observer\",\"guest_mutations\":false,\"cpu_core\":\"normal\"}\n",sr_trace);
 }
 if(!sr_trace)return;
 if((sr_sessions>=sr_max_sessions&&sr_max_sessions)||PIC_Ticks>sr_deadline){
 fprintf(sr_trace,"{\"kind\":\"stop\",\"ms\":%.6f,\"sessions\":%u,\"attempts\":%u,\"ticks\":%u}\n",double(PIC_FullIndex()),sr_sessions,sr_attempt,sr_ticks);fclose(sr_trace);exit(0);}
 unsigned ip=reg_eip&65535;
 if(!sr_cs){if(ip!=0x1b8)return;
 const unsigned char signature[]={0xc8,8,0,0,0x56,0x57,0xc7,0x46};
 for(unsigned i=0;i<sizeof(signature);i++)if(mem_readb(SegPhys(cs)+ip+i)!=signature[i])return;
 sr_cs=SegValue(cs);sr_ds=SegValue(ds);sr_log("main",false);}
 if(SegValue(cs)!=sr_cs)return;
 switch(ip){
 case 0x12f8:if(sr_hud&&sr_bp)sr_log("hud_step");
 if(sr_hud&&sr_bp&&(sr_hud_count++%8==0)){
 sr_hud_id++;sr_hud_pending=true;sr_hud_log("hud_before");sr_hud_dump("before.bin",0xa0000,64000);
 if(sr_hud_attempt!=sr_attempt){sr_hud_attempt=sr_attempt;
 sr_hud_dump("speed.bin",(PhysPt(sr_word(0x54a6))<<4)+sr_word(0x54a4),3835);
 sr_hud_dump("oxygen.bin",(PhysPt(sr_word(0x5476))<<4)+sr_word(0x5474),375);
 sr_hud_dump("fuel.bin",(PhysPt(sr_word(0x9610))<<4)+sr_word(0x960e),387);
 sr_hud_dump("symbols.bin",(PhysPt(sr_ds)<<4)+0x16c,460);
 }
 }break;
 case 0x1630:if(sr_hud_pending){sr_hud_dump("after.bin",0xa0000,64000);sr_hud_log("hud_after");sr_hud_pending=false;}break;
 case 0x57c4:if(sr_audio)sr_audio_score=sr_word(reg_sp+2);break;
 case 0x5a7d:if(sr_audio){sr_audio_start=sr_audio_irq;
 fprintf(sr_trace,"{\"kind\":\"music_start\",\"ms\":%.6f,\"irq\":%u,\"score\":%u,\"stream\":%u,\"instruments\":%u,\"length\":%u,\"delay\":%u}\n",double(PIC_FullIndex()),sr_audio_irq,sr_audio_score,sr_word(reg_sp+2),sr_word(reg_sp+4),sr_word(reg_bp-2),unsigned(mem_readb((PhysPt(sr_ds)<<4)+0xc83)));
 char suffix[80];snprintf(suffix,sizeof(suffix),"music-%u.bin",sr_audio_score);sr_dump(suffix,sr_word(reg_sp+4),sr_word(reg_bp-2));
 }break;
 case 0x5a55:if(sr_audio)sr_audio_irq++;break;
 case 0x5892:if(sr_audio){
 fprintf(sr_trace,"{\"kind\":\"opl\",\"ms\":%.6f,\"irq\":%u,\"score_irq\":%u,\"score\":%u,\"register\":%u,\"value\":%u}\n",double(PIC_FullIndex()),sr_audio_irq,sr_audio_irq-sr_audio_start,sr_audio_score,unsigned(reg_al),unsigned(reg_ah));
 }break;
 case 0x03c2:if(sr_audio){sr_log("sound_request");}break;
 case 0x5b76:if(sr_audio){sr_log("sample_playback");
 fprintf(sr_trace,"{\"kind\":\"sample_arguments\",\"ms\":%.6f,\"offset\":%u,\"segment\":%u,\"constant\":%u,\"length\":%u}\n",double(PIC_FullIndex()),sr_word(reg_sp+2),sr_word(reg_sp+4),sr_word(reg_sp+6),sr_word(reg_sp+8));
 }break;
 case 0x2d1f:if(sr_graphics&&sr_bp&&sr_word(reg_sp)==0x0ec4&&(sr_gfx_count++%16==0)){
 sr_gfx_id++;sr_gfx_pending=true;sr_gfx_destination=sr_word(reg_sp+16);
 sr_log("render_before");
 fprintf(sr_trace,"{\"kind\":\"render_arguments\",\"id\":%u,\"attempt\":%u,\"args\":[",sr_gfx_id,sr_attempt);
 for(unsigned i=0;i<8;i++)fprintf(sr_trace,"%s%u",i?",":"",sr_word(reg_sp+2+i*2));fputs("]}\n",sr_trace);fflush(sr_trace);
 sr_gfx_dump("before.bin",PhysPt(sr_gfx_destination)<<4,64000);
 if(sr_gfx_attempt!=sr_attempt){sr_gfx_attempt=sr_attempt;
 sr_gfx_dump("background.bin",PhysPt(sr_word(0x5170))<<4,64000,true);
 sr_gfx_dump("cars.bin",PhysPt(sr_word(0xaf36))<<4,55440,true);
 sr_gfx_dump("palette.bin",(PhysPt(sr_ds)<<4)+0x41c2,768,true);
 }
 }break;
 case 0x2e6b:if(sr_gfx_pending){sr_gfx_dump("after.bin",PhysPt(sr_gfx_destination)<<4,64000);sr_log("render_after");sr_gfx_pending=false;}break;
 case 0x4591:if(sr_keyboard){sr_log("title",false);sr_press(KBD_enter,50);CaptureState|=CAPTURE_IMAGE;}break;
 case 0x4e52:if(sr_keyboard){sr_log("main_menu",false);CaptureState|=CAPTURE_IMAGE;}break;
 case 0x4fb4:if(sr_keyboard){sr_log("main_menu_ready",false);if(!sr_menus)sr_press(KBD_enter,100);CaptureState|=CAPTURE_IMAGE;}break;
 case 0x5180:if(sr_keyboard){sr_log("road_menu",false);sr_menu_stage=2;CaptureState|=CAPTURE_IMAGE;}break;
 case 0x5feb:if(sr_menus){sr_menu_wait();break;}if(sr_menu_stage==2){sr_menu_stage=0;sr_log("road_menu_ready",false);if(sr_gallery&&sr_attempt){sr_press(KBD_down,100,30);sr_press(KBD_enter,200);}else if(!sr_gallery&&sr_attempt==5){sr_press(KBD_right,100,30);sr_press(KBD_right,180,30);sr_press(KBD_right,260,30);sr_press(KBD_enter,400);}else sr_press(KBD_enter,100);CaptureState|=CAPTURE_IMAGE;}break;
 case 0x1fd9:sr_attempt++;sr_ticks=0;sr_shot_tick=0;sr_starting=true;sr_in_tick=false;sr_gfx_count=0;sr_hud_count=0;
 if(sr_keyboard){sr_schedule(KBD_up,true,1);
 if(sr_gallery||sr_menus)sr_press(KBD_esc,1200,50);
 else if(sr_attempt==1){sr_press(KBD_space,700,30);sr_press(KBD_p,1000,100);
 sr_press(KBD_space,1300,5);sr_schedule(KBD_up,false,1010);sr_schedule(KBD_up,true,1450);}
 else if(sr_attempt==2)sr_press(KBD_left,1000,100);
 else if(sr_attempt!=4&&sr_attempt!=6)sr_press(KBD_esc,2000,50);}
 break;
 case 0x20aa:if(sr_starting){sr_starting=false;sr_bp=reg_bp;sr_ds=SegValue(ds);sr_log("initial");
 sr_dump("road.bin",0x162c,sr_word(0x41c0)*14);sr_dump("demo.bin",0x961e,6398);CaptureState|=CAPTURE_IMAGE;}else sr_log("outer");break;
 case 0x2324:sr_ticks++;sr_in_tick=true;sr_log("tick_before");break;
 case 0x2afd:if(sr_in_tick){sr_log("tick_after");sr_in_tick=false;}break;
 case 0x0f05:sr_log("finish_start");sr_in_tick=false;CaptureState|=CAPTURE_IMAGE;break;
 case 0x0f3f:sr_log("finish_frame");break;
 case 0x2b0b:sr_log("attempt_return");CaptureState|=CAPTURE_IMAGE;break;
 case 0x0365:sr_log("session_return",false);sr_sessions++;if(sr_keyboard)sr_schedule(KBD_up,false,0.001);break;
 case 0x0f4e:if(sr_bp)sr_log("finish_after");break;
 case 0x0339:if(sr_sessions)sr_log("retry_branch",false);break;
 case 0x03b7:sr_log("selection_branch",false);break;
 case 0x0c98:if(sr_keyboard&&!sr_gallery&&sr_attempt==4){
 double row=double(sr_dword(0x9618))/65536.0;int target=(row>=16&&row<37)?26880:32768;
 int delta=target-int(sr_word(0xaf1c));int direction=abs(delta)<450?0:delta>0?1:-1;
 if(direction!=sr_policy_direction){if(sr_policy_direction)sr_schedule(sr_policy_direction>0?KBD_right:KBD_left,false,0.001);
 if(direction)sr_schedule(direction>0?KBD_right:KBD_left,true,0.01);sr_policy_direction=direction;}}
 if(sr_ticks>=sr_shot_tick){sr_shot_tick=sr_ticks+200;CaptureState|=CAPTURE_IMAGE;}break;
 case 0x20d9:case 0x21a8:case 0x227d:
 if(sr_pause_ip!=ip||sr_pause_mask!=sr_mask()||sr_pause_timer!=sr_word(0x1600)){
 sr_pause_ip=ip;sr_pause_mask=sr_mask();sr_pause_timer=sr_word(0x1600);
 sr_log(ip==0x20d9?"pause_release":ip==0x21a8?"pause_press":"pause_clear");}break;
 case 0x2280:sr_log("pause_resume");break;
 case 0x074c:sr_log("input_poll");break;
 case 0x0af6:if(sr_response&&sr_bp)sr_log("input_decoded");break;
 case 0x3bfd:if(sr_response&&sr_bp)sr_log("keyboard_irq");break;
 case 0x22ef:if(sr_response&&sr_bp)sr_log("scene_ready");break;
 case 0x4b8e:sr_log("fade_start",false);break;
 case 0x4c1c:sr_log("fade_return",false);break;
 case 0x4459:sr_log("notice_start",false);break;
 case 0x4482:sr_log("notice_return",false);break;
 default:break;
 }
}

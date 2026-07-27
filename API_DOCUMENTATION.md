# API 閹恒儱褰涢弬鍥ㄣ€?


> 妞ゅ湱娲? A12 閳?閺呴缚鍏樻径鍥嚦娑撳孩鏆€鐎涳附鍨氶弸婊咁吀閻炲棗閽╅崣? 
> 閸╄櫣顢呯捄顖氱窞: `/api/v1`  
> 缂佺喍绔撮崫宥呯安閺嶇厧绱? `Result<T>` (code=200 閹存劕濮? message 閹诲繗鍫? data 鐎圭偤妾弫鐗堝祦娴?  
> 閸掑棝銆夐崫宥呯安: `PageResult<T>` (total 閹粯鏆? page 瑜版挸澧犳い? size 濮ｅ繘銆夐弶鈩冩殶, records 閸掓銆?

---

# 娑撯偓閵嗕浇顓荤拠浣鼓侀崸?

## API-01 POST /api/v1/auth/register

**閸旂喕鍏?*: 濞夈劌鍞介弫娆忕瑎鐠愶箑褰块妴鍌氬帥闁俺绻?API-02 閸欐垿鈧線鐛欑拠浣虹垳閸掍即鍋栫粻鎲嬬礉閸愬秴鐨㈡宀冪槈閻浇绻涢崥灞炬暈閸愬奔淇婇幁顖涘絹娴溿倛鍤﹀銈嗗复閸欙絻鈧倹婀囬崝锛勵伂閺嶏繝鐛欐宀冪槈閻礁鎮楅崚娑樼紦鐠愶箑褰块敍鍫㈡纯閹恒儲绺哄ú浼欑礉is_active=1閿?

**鐠囬攱鐪版担?(JSON)**
| 鐎涙顔?| 缁鐎?| 韫囧懎锝?| 鐠囧瓨妲?|
|---|---|---|---|
| `username` | String | **閺?* | 閻ц缍嶉悽銊﹀煕閸?|
| `password` | String | **閺?* | 鐎靛棛鐖滈敍鍫濆缁旑垯绱堕弰搴㈡瀮閿涘苯鎮楃粩顖氭惐鐢苯鎮楃€涙ê鍋嶉敍?|
| `real_name` | String | **閺?* | 閻喎鐤勬慨鎾虫倳 |
| `phone` | String | **閺?* | 閹靛婧€閸?|
| `email` | String | **閺?* | 闁喚顔?|
| `avatar` | String | 閸?| 婢舵潙鍎?URL |

**閸氬海顏?DTO**: ``

**閸濆秴绨?VO**: `Result<UserVO>` 閳?濞夈劌鍞介幋鎰鏉╂柨娲栭悽銊﹀煕娣団剝浼?

---

## API-02 POST /api/v1/auth/verification-codes

**閸旂喕鍏?*: 閸欐垿鈧線鍋栫粻閬嶇崣鐠囦胶鐖?

**鐠囬攱鐪版担?(JSON)**
| 鐎涙顔?| 缁鐎?| 韫囧懎锝?| 鐠囧瓨妲?|
|---|---|---|---|
| `username` | String | **閺?* | 濞夈劌鍞介崷鐑樻珯婵夘偊鍋栫粻鎲嬬礉鐎靛棛鐖滈柌宥囩枂閸︾儤娅欐繅顐ゆ暏閹村嘲鎮?|
| `scene` | String | **閺?* | 閸︾儤娅? `register` / `password_reset` |
| `channel` | String | **閺?* | 閸欐垿鈧焦绗柆? 娴犲懏鏁幐?`email` |

**閸氬海顏?DTO**: 閺嗗倹妫ら悪顒傜彌 DTO

**閸濆秴绨?VO**: `Result<Void>` 閳?娴犲懓绻戦崶鐐村灇閸?婢惰精瑙﹂悩鑸碘偓?

---

## API-03 POST /api/v1/auth/verify

**閸旂喕鍏?*: 閺嶏繝鐛欐宀冪槈閻緤绱欓惄顔煎娴犲懐鏁ゆ禍搴＄槕閻線鍣哥純顔兼簚閺咁垽绱卞▔銊ュ斀閸︾儤娅欓惃鍕崣鐠囦胶鐖滈弽锟犵崣閸?API-01 娑擃厼鐣幋鎰剁礆

**鐠囬攱鐪版担?(JSON)**
| 鐎涙顔?| 缁鐎?| 韫囧懎锝?| 鐠囧瓨妲?|
|---|---|---|---|
| `username` | String | **閺?* | 鐠愶箑褰?|
| `code` | String | **閺?* | 妤犲矁鐦夐惍?|
**閸氬海顏?DTO**: 閺嗗倹妫ら悪顒傜彌 DTO

**閸濆秴绨?VO**: `Result<Void>`

---

## API-04 POST /api/v1/auth/login

**閸旂喕鍏?*: 缂佺喍绔存宀冪槈娑撳琚拹锕€褰块敍鍫熸殌鐢?鐎光剝鐗抽崨?閸氬骸褰寸粻锛勬倞閸涙﹫绱?

**鐠囬攱鐪版担?(JSON)**
| 鐎涙顔?| 缁鐎?| 韫囧懎锝?| 鐠囧瓨妲?|
|---|---|---|---|
| `username` | String | **閺?* | 鐠愶箑褰?|
| `password` | String | **閺?* | 鐎靛棛鐖滈敍鍫濆缁旑垯绱堕弰搴㈡瀮閿涘苯鎮楃粩顖氭惐鐢苯鎮楃€涙ê鍋嶉敍?|

**閸氬海顏?DTO**: `LoginDTO { username, password }`

**閸濆秴绨?VO**: `Result<LoginVO>` 閳?閸?token閵嗕胶鏁ら幋宄扮唨閺堫兛淇婇幁顖樷偓浣筋潡閼瑰弶娼堥梽?

| LoginVO 鐎涙顔?| 缁鐎?| 鐠囧瓨妲?|
|---|---|---|
| `token` | String | 娴兼俺鐦芥禒銈囧 |
| `user_id` | int | 閻劍鍩汭D |
| `username` | String | 閻劍鍩涢崥?|
| `real_name` | String | 閻喎鐤勬慨鎾虫倳 |
| `avatar` | String | 婢舵潙鍎歎RL |
| `user_type` | String | 閻劍鍩涚猾璇茬€? `teacher` / `admin` |
| `roles` | String(JSON) | 鐟欐帟澹婇崚妤勩€?|
| `permissions` | String(JSON) | 閺夊啴妾洪崚妤勩€?|
| `created_at` | LocalDateTime | 閻ц缍嶉弮鍫曟？ |

## API-05 POST /api/v1/auth/initial-password-change

**閸旂喕鍏?*: 閹靛綊鍣洪崚娑樼紦鐠愶箑褰块崥搴浕濞嗭紕娅ヨぐ鏇㈡付瀵搫鍩楅弨鐟扮槕

**鐠囬攱鐪版担?(JSON)**
| 鐎涙顔?| 缁鐎?| 韫囧懎锝?| 鐠囧瓨妲?|
|---|---|---|---|
| `username` | String | **閺?* | 鐠愶箑褰?|
| `initial_password` | String | **閺?* | 閸掓繂顫愮€靛棛鐖滈敍鍫濆缁旑垯绱堕弰搴㈡瀮閿涘苯鎮楃粩顖氭惐鐢苯鎮楅弽锟犵崣閿?|
| `new_password` | String | **閺?* | 閺傛澘鐦戦惍渚婄礄閸撳秶顏导鐘虫閺傚浄绱濋崥搴ｎ伂閸濆牆绗囬崥搴＄摠閸岊煉绱?|

**閸氬海顏?DTO**: 閺嗗倹妫ら悪顒傜彌 DTO

**閸濆秴绨?VO**: `Result<LoginVO>` 閳?閺€鐟扮槕閹存劕濮涢崥搴ｎ劮閸欐垶顒滅敮闀愮窗鐠?

---

## API-06 POST /api/v1/auth/password-reset

**閸旂喕鍏?*: 闁俺绻冩宀冪槈閻線鍣哥純顔肩槕閻?

**鐠囬攱鐪版担?(JSON)**
| 鐎涙顔?| 缁鐎?| 韫囧懎锝?| 鐠囧瓨妲?|
|---|---|---|---|
| `username` | String | **閺?* | 鐠愶箑褰?|
| `code` | String | **閺?* | 鐎靛棛鐖滈柌宥囩枂妤犲矁鐦夐惍?|
| `new_password` | String | **閺?* | 閺傛澘鐦戦惍渚婄礄閸撳秶顏导鐘虫閺傚浄绱濋崥搴ｎ伂閸濆牆绗囬崥搴＄摠閸岊煉绱?|

**閸氬海顏?DTO**: 閺嗗倹妫ら悪顒傜彌 DTO

**閸濆秴绨?VO**: `Result<Void>` 閳?閹存劕濮涢崥搴㈡寵闁库偓閹碘偓閺堝鍑￠張澶夌窗鐠?

---

## API-07 POST /api/v1/users/me/password-change

**閸旂喕鍏?*: 瀹歌尙娅ヨぐ鏇犳暏閹磋渹鎱ㄩ弨鐟扮秼閸撳秴鐦戦惍?

**鐠囬攱鐪版担?(JSON)**
| 鐎涙顔?| 缁鐎?| 韫囧懎锝?| 鐠囧瓨妲?|
|---|---|---|---|
| `current_password` | String | **閺?* | 瑜版挸澧犵€靛棛鐖滈敍鍫濆缁旑垯绱堕弰搴㈡瀮閿涘苯鎮楃粩顖氭惐鐢苯鎮楅弽锟犵崣閿?|
| `new_password` | String | **閺?* | 閺傛澘鐦戦惍渚婄礄閸撳秶顏导鐘虫閺傚浄绱濋崥搴ｎ伂閸濆牆绗囬崥搴＄摠閸岊煉绱?|

**閸氬海顏?DTO**: 閺嗗倹妫ら悪顒傜彌 DTO

**閸濆秴绨?VO**: `Result<Void>` 閳?閺囧瓨鏌婄€靛棛鐖滈崥搴㈠瘻缁涙牜鏆愰幘銈夋敘閸忔湹绮导姘崇樈

---

## API-08 POST /api/v1/auth/logout

**閸旂喕鍏?*: 闁偓閸戣櫣娅ヨぐ鏇礉閹俱倝鏀㈣ぐ鎾冲娴兼俺鐦?

**鐠囬攱鐪版径?*: `Authorization: Bearer <token>`

**閸氬海顏崣鍌涙殶**: 閺冪姾顕Ч鍌欑秼閿涘奔绮犵拠閿嬬湴婢剁骞忛崣鏉ken

**閸濆秴绨?VO**: `Result<Void>`

---

# 娴滃被鈧胶鏁ら幋閿嬆侀崸?

## API-09 GET /api/v1/users/me

**閸旂喕鍏?*: 閼惧嘲褰囪ぐ鎾冲閻劍鍩涢妴浣筋潡閼瑰眰鈧焦娼堥梽鎰┾偓浣戒粓缁粯鏌熷蹇撴嫲鐠愶箑褰块悩鑸碘偓?

**鐠囬攱鐪版径?*: `Authorization: Bearer <token>`

**閸氬海顏崣鍌涙殶**: 閺冪媴绱欐禒宥磂curityContext閼惧嘲褰囪ぐ鎾冲閻劍鍩涢敍?

**閸濆秴绨?VO**: `Result<UserVO>`

| UserVO 鐎涙顔?| 缁鐎?| 鐠囧瓨妲?|
|---|---|---|
| `id` | int | 閻劍鍩汭D |
| `username` | String | 閻劍鍩涢崥?|
| `real_name` | String | 閻喎鐤勬慨鎾虫倳 |
| `phone` | String | 閹靛婧€閸?|
| `email` | String | 闁喚顔?|
| `avatar` | String | 婢舵潙鍎歎RL |
| `user_type` | String | 閻劍鍩涚猾璇茬€?|
| `roles` | String(JSON) | 鐟欐帟澹婇崚妤勩€?|
| `permissions` | String(JSON) | 閺夊啴妾洪崚妤勩€?|
| `is_active` | int | 閺勵垰鎯佸┑鈧ú? 1閺?0閸?|
| `created_at` | LocalDateTime | 閸掓稑缂撻弮鍫曟？ |
| `updated_at` | LocalDateTime | 閺囧瓨鏌婇弮鍫曟？ |

---

## API-10 GET /api/v1/users/by-username

**閸旂喕鍏?*: 閺嶈宓侀悽銊﹀煕閸氬秵鐓＄拠銏㈡暏閹寸īD閸滃苯鐔€閺堫兛淇婇幁?
**閺屻儴顕楅崣鍌涙殶**: username(String, 韫囧懎锝? 閳?閻劍鍩涢崥?
**閸濆秴绨?VO**: Result<{id: int, username: String, real_name: String, email: String}>

---

## API-11 GET /api/v1/users/by-email

**閸旂喕鍏?*: 閺嶈宓侀柇顔绢唸閺屻儴顕楅悽銊﹀煕ID閸滃苯鐔€閺堫兛淇婇幁?
**閺屻儴顕楅崣鍌涙殶**: email(String, 韫囧懎锝? 閳?闁喚顔?
**閸濆秴绨?VO**: Result<{id: int, username: String, real_name: String, email: String}>

---
# 娑撳鈧竸I 閺佹瑥顒熷鏇熸惛

## API-12 POST /api/v1/ai/sessions

**閸旂喕鍏?*: 閸掓稑缂撴径鍥嚦娴兼俺鐦介敍灞惧絹娴溿倖鏋冪€涙ぜ鈧浇顕㈤棅鐐解偓浣稿棘閼板啳绁弬娆嶁偓涓糼ill閸滃矁顕崇粙瀣╀繆閹?

**鐠囬攱鐪版担?(JSON)**
| 鐎涙顔?| 缁鐎?| 韫囧懎锝?| 鐠囧瓨妲?|
|---|---|---|---|
| `title` | String | **閺?* | 娴兼俺鐦介弽鍥暯 |
| `subject` | String | **閺?* | 鐎涳妇顫?|
| `grade` | String | **閺?* | 楠炲楠?|
| `messages` | String(JSON) | 閸?| 閸掓繂顫愮€电鐦藉☉鍫熶紖 |
| `uploaded_refs` | String(JSON) | 閸?| 閸欏倽鈧啳绁弬姗閸掓銆?|
| `status` | String | 閸?| 姒涙顓?`active` |

**閸氬海顏?DTO**: `TaskCreateDTO { title, subject, grade, status, uploaded_refs, plan_json }`

**閸濆秴绨?VO**: `Result<TaskVO>` 閳?閸氼偂绱扮拠婊籇

---

## API-13 POST /api/v1/ai/sessions/{id}/messages

**閸旂喕鍏?*: 鐎电鐦芥稉顓∷夐崗鍛存付濮瑰倶鈧礁娲栫粵鏃€绶炲〒鍛存６妫版ɑ鍨ㄩ幓鎰唉閸欏秹顩?

**鐠侯垰绶為崣鍌涙殶**: `id` 閳?娴兼俺鐦絀D

**鐠囬攱鐪版担?(JSON)**
| 鐎涙顔?| 缁鐎?| 韫囧懎锝?| 鐠囧瓨妲?|
|---|---|---|---|
| `messages` | String(JSON) | **閺?* | 濞戝牊浼呴崘鍛啇閿涘湏rray of {role, content}閿?|

**閸氬海顏?DTO**: `ConversationDTO { title(闁锝?, status(闁锝?, messages, context_summary(闁锝? }`

**閸濆秴绨?VO**: `Result<ConversationVO>` 閳?閺囧瓨鏌婇崥搴ｆ畱娴兼俺鐦芥穱鈩冧紖

---

## API-14 GET /api/v1/ai/sessions/{id}/plan

**閸旂喕鍏?*: 閼惧嘲褰囪ぐ鎾冲閺佹瑥顒熺拋鎹愵吀婢堆呯堪閸欏﹦澧楅張?

**鐠侯垰绶為崣鍌涙殶**: `id` 閳?娴兼俺鐦絀D

**閸氬海顏崣鍌涙殶**: 閺冪姾顕Ч鍌欑秼

**閸濆秴绨?VO**: `Result<TaskVO>` 閳?閸忔湹鑵戦惃?`plan_json` 閸?`plan_confirm_status` 鐎涙顔岄崠鍛儓婢堆呯堪閸愬懎顔?

---

## API-15 POST /api/v1/ai/sessions/{id}/plan-confirmations

**閸旂喕鍏?*: 绾喛顓婚妴渚€鈧偓閸ョ偞鍨ㄧ悰銉ュ帠閺佹瑥顒熺拋鎹愵吀婢堆呯堪

**鐠侯垰绶為崣鍌涙殶**: `id` 閳?娴兼俺鐦絀D

**鐠囬攱鐪版担?(JSON)**
| 鐎涙顔?| 缁鐎?| 韫囧懎锝?| 鐠囧瓨妲?|
|---|---|---|---|
| `action` | String | **閺?* | 閹垮秳缍? `confirm` / `reject` / `supplement` |
| `comment` | String | 閸?| 闁偓閸ョ偞鍨ㄧ悰銉ュ帠鐠囧瓨妲?|
| `plan_version` | int | **閺?* | 婢堆呯堪閻楀牊婀伴崣鍑ょ礄闂冩彃鑻熼崣鎴濆暱缁愪緤绱?|

**閸氬海顏?DTO**: 閺嗗倹妫ら悪顒傜彌 DTO

**閸濆秴绨?VO**: `Result<Void>`

---

## API-16 POST /api/v1/ai/sessions/{id}/runs

**閸旂喕鍏?*: 娓氭繃宓佸鑼€樼拋銈堫吀閸掓帒鍨卞鐑樺⒔鐞涘奔鎹㈤崝?

**鐠侯垰绶為崣鍌涙殶**: `id` 閳?娴兼俺鐦絀D

**閸氬海顏崣鍌涙殶**: 閺冪姾顕Ч鍌欑秼

**閸濆秴绨?VO**: `Result<TaskVO>` 閳?閸氼偂鎹㈤崝顡廌閿涘tatus 鏉烆兛璐?`running`

---

## API-17 GET /api/v1/ai/runs/{runId}

**閸旂喕鍏?*: 閺屻儴顕楅悽鐔稿灇閵嗕礁寮介幀婵嗗挤婢惰精瑙﹂悩鑸碘偓?

**鐠侯垰绶為崣鍌涙殶**: `runId` 閳?閹笛嗩攽娴犺濮烮D

**閸氬海顏崣鍌涙殶**: 閺冪姾顕Ч鍌欑秼

**閸濆秴绨?VO**: `Result<TaskVO>`

---

## API-18 GET /api/v1/ai/runs/{runId}/events

**閸旂喕鍏?*: 闁俺绻?SSE 閹恒儲鏁归梼鑸殿唽閵嗕浇绻樻惔锕€鎷版０鍕潔閺囧瓨鏌婇敍灞炬暜閹镐焦鏌囩痪璺ㄧ敾娴?

**鐠侯垰绶為崣鍌涙殶**: `runId` 閳?閹笛嗩攽娴犺濮烮D

**閺屻儴顕楅崣鍌涙殶**:
| 鐎涙顔?| 缁鐎?| 韫囧懎锝?| 鐠囧瓨妲?|
|---|---|---|---|
| `lastEventId` | String | 閸?| 閺傤厾鍤庣紒顓濈炊閺冭埖鎯＄敮锔芥付閸氬孩鏁归崚鎵畱 eventId |

**閸氬海顏?DTO**: 閺冪媴绱濆ù浣哥础鏉╂柨娲?

**閸濆秴绨?*: 鏉╂柨娲?`text/event-stream`閿涘湯SE閿涘绱濋崠鍛儓闂冭埖顔屾潻娑樺閸滃矂顣╃憴鍫熸殶閹?

---

# 閸ユ稏鈧線銆嶉惄顔侥侀崸?
> **閺夊啴妾虹拠瀛樻**閿涙碍澧嶉張澶愭付鐟曚礁顕い鍦窗鏉╂稖顢戦崘娆愭惙娴ｆ粎娈戦幒銉ュ經閿涘苯娼庨棁鈧弽锟犵崣瑜版挸澧犻悽銊﹀煕閺勵垰鎯佹稉娲€嶉惄顔藉閺堝鈧拑绱檜ser_id == currentId閿涘鍨ㄧ悮顐ｅ房閺夊啰鏁ら幋鍑ょ礄currentId 鐎涙ê婀禍?permissions JSON 閺佹壆绮嶆稉顓ㄧ礆閵?
## API-20 POST /api/v1/projects

**閸旂喕鍏?*: 閸掓稑缂撴稉顏冩眽閺佹瑥顒熸い鍦窗閹存牜銇為崠鐑樻烦閻㈢喖銆嶉惄?

**鐠囬攱鐪版担?(JSON)**
| 鐎涙顔?| 缁鐎?| 韫囧懎锝?| 鐠囧瓨妲?|
|---|---|---|---|
| `project_name` | String | **閺?* | 妞ゅ湱娲伴崥宥囆?|
| `project_type` | String | **閺?* | 缁鐎? `ppt` / `word` / `h5` / `mixed` |
| `status` | String | 閸?| 姒涙顓?`draft` |
| `snapshots` | String(JSON) | 閸?| 閻楀牊婀拌箛顐ゅ弾閸掓銆?|
| `edit_history` | String(JSON) | 閸?| 缂傛牞绶崢鍡楀蕉 |

**閸氬海顏?DTO**: `ProjectCreateDTO { project_name, project_type, status, snapshots, edit_history }`

**閸濆秴绨?VO**: `Result<ProjectVO>`

---

## API-21 GET /api/v1/projects

**閸旂喕鍏?*: 閹稿鎮曠粔鑸偓浣筋嚦缁嬪鈧焦鍨氶弸婊呰閸ㄥ鈧胶濮搁幀浣告嫲閺囧瓨鏌婇弮鍫曟？閸掑棝銆夐弻銉嚄妞ゅ湱娲?

**閺屻儴顕楅崣鍌涙殶**:
| 鐎涙顔?| 缁鐎?| 韫囧懎锝?| 鐠囧瓨妲?|
|---|---|---|---|
| `keyword` | String | 閸?| 閸氬秶袨/鐠囧墽鈻奸崗鎶芥暛鐎涙膩缁﹥鎮崇槐?|
| `project_type` | String | 閸?| 缁涙盯鈧琚崹? `ppt`/`word`/`h5`/`mixed` |
| `status` | String | 閸?| 缁涙盯鈧濮搁幀? `draft`/`editing`/`confirmed`/`exported` |
| `user_id` | Integer | 閸?| 缁涙盯鈧鏁ら幋鍑ょ礄閸氬海顏懛顏勫З鐠佸彞璐熻ぐ鎾冲閻劍鍩涢敍?|
| `page` | int | 閸?| 姒涙顓? |
| `size` | int | 閸?| 姒涙顓?0 |

**閸氬海顏?DTO**: `ProjectQueryDTO extends PageQuery { user_id, project_type, status, keyword }`

**閸濆秴绨?VO**: `Result<PageResult<ProjectVO>>`

---

## API-22 GET /api/v1/projects/{id}

**閸旂喕鍏?*: 閼惧嘲褰囨い鍦窗閸愬懎顔愰妴浣稿帗閺佺増宓侀妴浣哥秼閸撳秶澧楅張顒€鎷伴弶鍐

**鐠侯垰绶為崣鍌涙殶**: `id` 閳?妞ゅ湱娲癐D

**閸濆秴绨?VO**: `Result<ProjectVO>`

---

## API-23 PATCH /api/v1/projects/{id}

**閸旂喕鍏?*: 娣囶喗鏁兼い鍦窗閸氬秶袨閵嗕胶琚崹瀣ㄢ偓浣哄Ц閹胶鐡戦崗鍐╂殶閹诡噯绱濇担璺ㄦ暏閻楀牊婀伴崣鐑芥Щ楠炶泛褰傜憰鍡欐磰

**鐠侯垰绶為崣鍌涙殶**: `id` 閳?妞ゅ湱娲癐D

**鐠囬攱鐪版担?(JSON)**
| 鐎涙顔?| 缁鐎?| 韫囧懎锝?| 鐠囧瓨妲?|
|---|---|---|---|
| `project_name` | String | 閸?| 閺傛澘鎮曠粔?|
| `project_type` | String | 閸?| 閺傛壆琚崹?|
| `status` | String | 閸?| 閺傛壆濮搁幀?|
| `current_version` | int | **閺?* | 瑜版挸澧犻悧鍫熸拱閸欏嚖绱欐稊鎰潎闁夸緤绱濋梼鍙夘剾鐟曞棛娲婇敍?|

**閸氬海顏?DTO**: `ProjectCreateDTO`

**閸濆秴绨?VO**: `Result<ProjectVO>`

---

## API-24 POST /api/v1/projects/{id}/copies

**閸旂喕鍏?*: 婢跺秴鍩楅張澶嬫綀鐠佸潡妫堕惃鍕€嶉惄顔艰嫙閸掓稑缂撻弬鎵畱缁変焦婀佹い鍦窗

**鐠侯垰绶為崣鍌涙殶**: `id` 閳?濠ф劙銆嶉惄鐢€D

**鐠囬攱鐪版担?(JSON)**
| 鐎涙顔?| 缁鐎?| 韫囧懎锝?| 鐠囧瓨妲?|
|---|---|---|---|
| `new_name` | String | 閸?| 閺備即銆嶉惄顔兼倳缁夊府绱欐妯款吇閸樼喎鎮曠粔?閸擃垱婀伴敍?|

**閸氬海顏?DTO**: 閺嗗倹妫ら悪顒傜彌 DTO

**閸濆秴绨?VO**: `Result<ProjectVO>` 閳?閺備即銆嶉惄顔炬畱鐎瑰本鏆ｆ穱鈩冧紖

---

## API-25 POST /api/v1/projects/{id}/archive

**閸旂喕鍏?*: 瑜版帗銆傛い鍦窗閿涘瞼顩﹀銏㈡埛缂侇厾绱潏?

**鐠侯垰绶為崣鍌涙殶**: `id` 閳?妞ゅ湱娲癐D

**閸氬海顏崣鍌涙殶**: 閺冪姾顕Ч鍌欑秼

**閸濆秴绨?VO**: `Result<ProjectVO>` 閳?閻樿埖鈧焦娲块弬棰佽礋 `archived`

---

## API-26 POST /api/v1/projects/{id}/restore

**閸旂喕鍏?*: 鐏忓棗缍婂锝嗗灗閸欘垱浠径宥呭灩闂勩倗濮搁幀浣烘畱妞ゅ湱娲伴幁銏狀槻娑撳搫褰查悽?

**鐠侯垰绶為崣鍌涙殶**: `id` 閳?妞ゅ湱娲癐D

**閸氬海顏崣鍌涙殶**: 閺冪姾顕Ч鍌欑秼

**閸濆秴绨?VO**: `Result<ProjectVO>`

---

## API-27 DELETE /api/v1/projects/{id}

**閸旂喕鍏?*: 閺嶏繝鐛欓弶鍐閵嗕椒绻氶悾娆愭埂閸滃苯鍙ч懕鏂款嚤閸戣桨鎹㈤崝鈥虫倵濮橀晲绠欓崚鐘绘珟

**鐠侯垰绶為崣鍌涙殶**: `id` 閳?妞ゅ湱娲癐D

**閸氬海顏崣鍌涙殶**: 閺冪姾顕Ч鍌欑秼

**閸濆秴绨?VO**: `Result<Void>`

---

## API-28 POST /api/v1/projects/{id}/ai-revisions

**閸旂喕鍏?*: 鐎佃瀵氱€规岸銆夐棃銏″灗缂佸嫪娆㈤幍褑顢戦懛顏嗗姧鐠囶叀鈻堟穱顔芥暭

**鐠侯垰绶為崣鍌涙殶**: `id` 閳?妞ゅ湱娲癐D

**鐠囬攱鐪版担?(JSON)**
| 鐎涙顔?| 缁鐎?| 韫囧懎锝?| 鐠囧瓨妲?|
|---|---|---|---|
| `target_type` | String | **閺?* | 娣囶喗鏁奸惄顔界垼: `page` / `component` |
| `target_id` | String | **閺?* | 閻╊喗鐖ｉ弽鍥槕 |
| `instruction` | String | **閺?* | 閼奉亞鍔х拠顓♀枅娣囶喗鏁奸幐鍥︽姢 |
| `context` | String(JSON) | 閸?| 闂勫嫬濮炴稉濠佺瑓閺?|

**閸氬海顏?DTO**: 閺嗗倹妫ら悪顒傜彌 DTO

**閸濆秴绨?VO**: `Result<PageVO>` 閳?娣囶喗鏁奸崥搴ｆ畱妞ょ敻娼伴崘鍛啇

---

## API-29 POST /api/v1/projects/{id}/components

**閸旂喕鍏?*: 閹绘帒鍙嗛弬鍥ㄦ拱閵嗕礁娴橀悧鍥モ偓渚€鐓剁憴鍡涱暥閵嗕浇銆冮弽绗衡偓涓?閹存牕顒熺粔鎴濅紣閸忛绮嶆禒?

**鐠侯垰绶為崣鍌涙殶**: `id` 閳?妞ゅ湱娲癐D

**鐠囬攱鐪版担?(JSON)**
| 鐎涙顔?| 缁鐎?| 韫囧懎锝?| 鐠囧瓨妲?|
|---|---|---|---|
| `page_id` | int | **閺?* | 閻╊喗鐖ｆい鐢告桨ID |
| `page_order` | int | **閺?* | 妞ょ敻娼版い鍝勭碍 |
| `page_type` | String | **閺?* | 妞ょ敻娼扮猾璇茬€? `cover`/`toc`/`content`/`summary` |
| `page_title` | String | 閸?| 妞ょ敻娼伴弽鍥暯 |
| `page_content` | String(JSON) | 閸?| 妞ょ敻娼伴崘鍛啇 |
| `components` | String(JSON) | 閸?| 缂佸嫪娆㈤崚妤勩€?|

**閸氬海顏?DTO**: `PageDTO { page_order, page_type, page_title, page_content, components }`

**閸濆秴绨?VO**: `Result<PageVO>`

---

## API-30 PATCH /api/v1/projects/{id}/components/{componentId}

**閸旂喕鍏?*: 娣囶喗鏁肩紒鍕閸愬懎顔愰妴浣风秴缂冾喖鎷伴弽宄扮础

**鐠侯垰绶為崣鍌涙殶**: `id` 閳?妞ゅ湱娲癐D, `componentId` 閳?缂佸嫪娆D

**鐠囬攱鐪版担?(JSON)**
| 鐎涙顔?| 缁鐎?| 韫囧懎锝?| 鐠囧瓨妲?|
|---|---|---|---|
| `page_content` | String(JSON) | 閸?| 閺囧瓨鏌婇惃鍕€夐棃銏犲敶鐎?|
| `components` | String(JSON) | 閸?| 閺囧瓨鏌婇惃鍕矋娴犺泛鍨悰?|

**閸氬海顏?DTO**: `PageDTO`

**閸濆秴绨?VO**: `Result<PageVO>`

---

## API-31 POST /api/v1/projects/{id}/versions

**閸旂喕鍏?*: 娣囨繂鐡ㄦ稉宥呭讲閸欐﹢銆嶉惄顔惧閺堫剙鑻熸潻鏂挎礀閻楀牊婀扮紓鏍у娇

**鐠侯垰绶為崣鍌涙殶**: `id` 閳?妞ゅ湱娲癐D

**鐠囬攱鐪版担?(JSON)**
| 鐎涙顔?| 缁鐎?| 韫囧懎锝?| 鐠囧瓨妲?|
|---|---|---|---|
| `description` | String | 閸?| 閻楀牊婀扮拠瀛樻 |

**閸氬海顏?DTO**: 閺嗗倹妫ら悪顒傜彌 DTO

**閸濆秴绨?VO**: `Result<{version_id: int, version_number: int}>`

---

## API-32 GET /api/v1/projects/{id}/versions

**閸旂喕鍏?*: 閸掑棝銆夐弻銉嚄妞ゅ湱娲伴崢鍡楀蕉閻楀牊婀伴妴浣稿灡瀵よ桨姹夐妴浣筋嚛閺勫骸鎷伴崚娑樼紦閺冨爼妫?

**鐠侯垰绶為崣鍌涙殶**: `id` 閳?妞ゅ湱娲癐D

**閺屻儴顕楅崣鍌涙殶**:
| 鐎涙顔?| 缁鐎?| 韫囧懎锝?| 鐠囧瓨妲?|
|---|---|---|---|
| `page` | int | 閸?| 姒涙顓? |
| `size` | int | 閸?| 姒涙顓?0 |

**閸氬海顏?DTO**: `PageQuery { page, size }`

**閸濆秴绨?VO**: `Result<PageResult<{version_id, version_number, description, created_at}>>`

---

## API-33 GET /api/v1/projects/{id}/versions/{versionId}/diff

**閸旂喕鍏?*: 鐏忓棛娲伴弽鍥╁閺堫兛绗岄幐鍥х暰閻楀牊婀伴幋鏍х秼閸撳秶澧楅張顒冪箻鐞涘苯妯婂鍌涚槷鏉?

**鐠侯垰绶為崣鍌涙殶**: `id` 閳?妞ゅ湱娲癐D, `versionId` 閳?閻╊喗鐖ｉ悧鍫熸拱ID

**閺屻儴顕楅崣鍌涙殶**:
| 鐎涙顔?| 缁鐎?| 韫囧懎锝?| 鐠囧瓨妲?|
|---|---|---|---|
| `compare_version_id` | Integer | 閸?| 鐎佃鐦悧鍫熸拱ID閿涘牅绗夋导鐘插灟濮ｆ棁绶濊ぐ鎾冲閻楀牊婀伴敍?|

**閸濆秴绨?VO**: `Result<{differences: Array, summary: String}>`

---

## API-34 POST /api/v1/projects/{id}/versions/{versionId}/restore

**閸旂喕鍏?*: 閸╄桨绨崢鍡楀蕉閻楀牊婀伴崚娑樼紦閺傛壆娈戣ぐ鎾冲閻楀牊婀伴敍灞肩瑝娣囶喗鏁奸崢鐔峰坊閸欒尪顔囪ぐ?

**鐠侯垰绶為崣鍌涙殶**: `id` 閳?妞ゅ湱娲癐D, `versionId` 閳?濠ф劗澧楅張鐞丏

**閸氬海顏崣鍌涙殶**: 閺冪姾顕Ч鍌欑秼

**閸濆秴绨?VO**: `Result<ProjectVO>` 閳?閹垹顦查崥搴ｆ畱妞ゅ湱娲伴敍鍧坲rrent_version 闁帒顤冮敍?

---

## API-35 POST /api/v1/projects/{id}/permissions

**功能**: 添加项目授权用户。仅项目创建者(拥有者)可以调用，将被授权用户的ID加入到项目的 `permissions` JSON 数组中(去重)。

**路径参数**: `id` -- 项目ID

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `user_id` | Integer | **是** | 要授权的用户ID(需已注册) |

**后端 DTO**: `ProjectPermissionDTO { user_id }`

**响应 VO**: `Result<ProjectVO>` -- 更新后的项目信息(含最新的 `permissions` 列表)

# 娴滄柣鈧椒閲滄禍楦跨カ濠ф劕绨?

## API-36 POST /api/v1/resources/upload-tokens
 
 **閸旂喕鍏?*: 閼惧嘲褰?OSS 缁涙儳鎮曟稉濠佺炊 URL閵嗗倸鎮楃粩顖滄晸閹存劕鏁稉鈧?objectKey 楠炴儼绻戦崶鐐殿劮閸?PUT URL閿涘苯澧犵粩顖涘瑏閸?URL 閸氬海娲挎导鐘绘▼闁插奔绨?OSS
 
 **鐠囬攱鐪版担?(JSON)**
 | 鐎涙顔?| 缁鐎?| 韫囧懎锝?| 鐠囧瓨妲?|
 |---|---|---|---|
 | `file_name` | String | **閺?* | 閺傚洣娆㈤崥?|
 | `file_type` | String | 閸?| 閺傚洣娆㈢猾璇茬€? `word`/`pdf`/`ppt`/`txt`/`image`/`audio`/`video`閿涘牅绗夋导鐘插灟閺嶈宓侀幍鈺佺潔閸氬秷鍤滈崝銊︻梾濞村绱?|
 | `description` | String | 閸?| 閺傚洣娆㈤幓蹇氬牚 |
 | `replace_target_id` | Integer | 閸?| 鐟曚焦娴涢幑銏㈡畱鐠у嫭绨甀D閿涘牊娴涢幑銏℃閸氬海顏导姘閻炲棙妫弬鍥︽楠炴儼钂嬮崚鐘绘珟閺冄嗩唶瑜版洩绱?|
 
 **閸氬海顏?DTO**: `UploadTokenDTO { file_name, file_type, description, replace_target_id }`
 
 **閸濆秴绨?VO**: `Result<UploadTokenVO>`
 
 | UploadTokenVO 鐎涙顔?| 缁鐎?| 鐠囧瓨妲?|
 |---|---|---|
 | `object_key` | String | OSS 鐎电钖勯柨?|
 | `upload_url` | String | 缁涙儳鎮?PUT URL閿涘牊婀侀弫鍫熸埂60閸掑棝鎸撻敍?|
 | `expires_at` | LocalDateTime | URL 鏉╁洦婀￠弮鍫曟？ |
 
 ---
 
## API-37 POST /api/v1/resources/uploaded-files
 
 **閸旂喕鍏?*: 閸撳秶顏惄缈犵炊 OSS 閹存劕濮涢崥搴ㄢ偓姘辩叀閸氬海顏涵顔款吇閵嗗倸鎮楃粩顖炵崣鐠囦焦鏋冩禒璺哄嚒鐎涙ê婀禍?OSS閿涘苯鍨卞楦跨カ濠ф劘顔囪ぐ鏇炶嫙鐎涙ê鍙嗛弫鐗堝祦鎼?
 
 **鐠囬攱鐪版担?(JSON)**
 | 鐎涙顔?| 缁鐎?| 韫囧懎锝?| 鐠囧瓨妲?|
 |---|---|---|---|
 | `object_key` | String | **閺?* | API-36 鏉╂柨娲栭惃?object_key |
 | `file_name` | String | **閺?* | 閺傚洣娆㈤崥?|
 | `file_size` | long | **閺?* | 閺傚洣娆㈡径褍鐨敍鍫濈摟閼哄偊绱?|
 | `file_type` | String | 閸?| 閺傚洣娆㈢猾璇茬€烽敍灞肩瑝娴肩姴鍨弽瑙勫祦閹碘晛鐫嶉崥宥堝殰閸斻劍顥呭ù?|
 | `description` | String | 閸?| 閺傚洣娆㈤幓蹇氬牚 |
 | `replace_target_id` | Integer | 閸?| 鐟曚焦娴涢幑銏㈡畱鐠у嫭绨甀D |
 
 **閸氬海顏?DTO**: `ResourceUploadConfirmDTO { object_key, file_name, file_size, file_type, description, replace_target_id }`
 
 **閸濆秴绨?VO**: `Result<MaterialVO>` 閳?鐠у嫭绨崗鍐╂殶閹?
 
 ---
 
## API-38 GET /api/v1/resources

**閸旂喕鍏?*: 閹稿鎮曠粔鑸偓浣筋嚦缁嬪鈧胶鐝烽懞鍌樷偓浣虹叀鐠囧棛鍋ｉ妴浣圭垼缁涗勘鈧胶琚崹瀣嫲閺冨爼妫块崚鍡涖€夊Λ鈧槐銏ｇカ濠?

**閺屻儴顕楅崣鍌涙殶**:
| 鐎涙顔?| 缁鐎?| 韫囧懎锝?| 鐠囧瓨妲?|
|---|---|---|---|
| `keyword` | String | 閸?| 閸氬秶袨閸忔娊鏁€?|
| `file_type` | String | 閸?| 缁涙盯鈧鏋冩禒鍓佽閸?|
| `user_id` | Integer | 閸?| 缁涙盯鈧鏁ら幋鍑ょ礄閸氬海顏懛顏勫З鐠佸彞璐熻ぐ鎾冲閻劍鍩涢敍?|
| `page` | int | 閸?| 姒涙顓? |
| `size` | int | 閸?| 姒涙顓?0 |

**閸氬海顏?DTO**: `MaterialQueryDTO extends PageQuery { user_id, file_type, keyword }`

**閸濆秴绨?VO**: `Result<PageResult<MaterialVO>>`

---

## API-39 GET /api/v1/resources/{id}

**閸旂喕鍏?*: 閼惧嘲褰囩挧鍕爱閸忓啯鏆熼幑顔衡偓浣稿瀻缁眹鈧浇袙閺嬫劗濮搁幀浣告嫲瑜版挸澧犻弶鍐閹芥顩?

**鐠侯垰绶為崣鍌涙殶**: `id` 閳?鐠у嫭绨甀D

**閸濆秴绨?VO**: `Result<MaterialVO>`

---

## API-40 PATCH /api/v1/resources/{id}

**閸旂喕鍏?*: 缂傛牞绶挧鍕爱閸氬秶袨閵嗕焦鐖ｇ粵淇扁偓浣筋嚦缁嬪鈧礁鍨庣猾缁樺灗閹碘偓閸︺劎娲拌ぐ?

**鐠侯垰绶為崣鍌涙殶**: `id` 閳?鐠у嫭绨甀D

**鐠囬攱鐪版担?(JSON)** 閳?娴犮儰绗呴崸鍥﹁礋闁锝?
| 鐎涙顔?| 缁鐎?| 韫囧懎锝?| 鐠囧瓨妲?|
|---|---|---|---|
| `file_name` | String | 閸?| 閺傜増鏋冩禒璺烘倳 |
| `description` | String | 閸?| 閺傜増寮挎潻?|
| `categories` | String(JSON) | 閸?| 閺傛澘鍨庣猾?|
| `tags` | String(JSON) | 閸?| 閺傜増鐖ｇ粵?|

**閸氬海顏?DTO**: `MaterialDTO`閿涘牅绮庢导鐘烩偓鎺撴纯閺傛壆娈戠€涙顔岄敍?

**閸濆秴绨?VO**: `Result<MaterialVO>`

---

## API-41 DELETE /api/v1/resources/{id}

**閸旂喕鍏?*: 閸掔娀娅庣挧鍕爱楠炴儼袝閸欐垵鍙ч懕鏃傜叀鐠囧棛鍌ㄥ鏇炰粻閻?

**鐠侯垰绶為崣鍌涙殶**: `id` 閳?鐠у嫭绨甀D

**閸氬海顏崣鍌涙殶**: 閺冪姾顕Ч鍌欑秼

**閸濆秴绨?VO**: `Result<Void>`

---

## API-42 POST /api/v1/resources/batch-actions

**閸旂喕鍏?*: 閹稿绠撶粵澶愭暛閹靛綊鍣虹粔璇插З閵嗕礁鍨庣猾缁樺灗閸掔娀娅庣挧鍕爱

**鐠囬攱鐪版担?(JSON)**
| 鐎涙顔?| 缁鐎?| 韫囧懎锝?| 鐠囧瓨妲?|
|---|---|---|---|
| `idempotent_key` | String | **閺?* | 楠炲倻鐡戦柨?|
| `action` | String | **閺?* | 閹垮秳缍? `move` / `categorize` / `delete` |
| `resource_ids` | Array[int] | **閺?* | 鐠у嫭绨甀D閸掓銆?|
| `target` | String | 閸?| 缁夎濮?閸掑棛琚惃鍕窗閺嶅洤鈧?|

**閸氬海顏?DTO**: 閺嗗倹妫ら悪顒傜彌 DTO

**閸濆秴绨?VO**: `Result<{results: Array<{id: int, success: boolean, error: String}>>}`

---

## API-43 GET /api/v1/resources/{id}/permission

**閸旂喕鍏?*: 閼惧嘲褰囩挧鍕爱缁変焦婀?閸忓彉闊╅悩鑸碘偓浣碘偓浣稿彙娴滎偄顕挒鈥冲挤鐠佸潡妫堕弶鍐

**鐠侯垰绶為崣鍌涙殶**: `id` 閳?鐠у嫭绨甀D

**閸濆秴绨?VO**: `Result<{access_type: String, authorized_users: String(JSON), allow_ai: int}>`

---

## API-44 PUT /api/v1/resources/{id}/permission

**閸旂喕鍏?*: 鐠佸墽鐤嗙挧鍕爱缁変焦婀侀悩鑸碘偓浣碘偓浣稿彙娴滎偄顕挒鈥冲挤鐠佸潡妫堕弶鍐

**鐠侯垰绶為崣鍌涙殶**: `id` 閳?鐠у嫭绨甀D

**鐠囬攱鐪版担?(JSON)**
| 鐎涙顔?| 缁鐎?| 韫囧懎锝?| 鐠囧瓨妲?|
|---|---|---|---|
| `access_type` | String | **閺?* | `private` / `shared` / `authorized` |
| `authorized_users` | String(JSON) | 閸?| 閹哄牊娼堥悽銊﹀煕ID閸掓銆?|
| `allow_ai` | int | 閸?| 閸忎浇顔廇I鐠佸潡妫? 1/0 |

**閸氬海顏?DTO**: `MaterialDTO { access_type, authorized_users, allow_ai }`

**閸濆秴绨?VO**: `Result<MaterialVO>`

---

## API-45 GET /api/v1/resources/{id}/audit-logs

**閸旂喕鍏?*: 閺屻儳婀呴弶鍐閸滃苯鍘撻弫鐗堝祦娣囶喗鏁肩拋鏉跨秿

**鐠侯垰绶為崣鍌涙殶**: `id` 閳?鐠у嫭绨甀D

**閺屻儴顕楅崣鍌涙殶**:
| 鐎涙顔?| 缁鐎?| 韫囧懎锝?| 鐠囧瓨妲?|
|---|---|---|---|
| `page` | int | 閸?| 姒涙顓? |
| `size` | int | 閸?| 姒涙顓?0 |

**閸濆秴绨?VO**: `Result<PageResult<LogVO>>`

---

## API-46 POST /api/v1/resources/{id}/download-url

**閸旂喕鍏?*: 閺嶏繝鐛欓弶鍐楠炲墎鏁撻幋鎰叚閺冩湹绗呮潪钘夋勾閸р偓

**鐠侯垰绶為崣鍌涙殶**: `id` 閳?鐠у嫭绨甀D
**閸氬海顏崣鍌涙殶**: 閺冪姾顕Ч鍌欑秼
**閸濆秴绨?VO**: `Result<{download_url: String, expires_at: LocalDateTime}>`

---

# 閸忣厹鈧焦鍨氶弸婊冾嚤閸戣桨鑵戣箛?

## API-47 POST /api/v1/projects/{id}/export-prechecks

**閸旂喕鍏?*: 濡偓閺屻儵銆嶉惄顔兼彥閻撗佲偓浣虹閺夋劑鈧礁鐡ф担鎾扁偓浣稿悑鐎硅鈧佲偓浣哄閺夊啫鎷伴弫蹇斿妳娣団剝浼?

**鐠侯垰绶為崣鍌涙殶**: `id` 閳?妞ゅ湱娲癐D
**鐠囬攱鐪版担?(JSON)**
| 鐎涙顔?| 缁鐎?| 韫囧懎锝?| 鐠囧瓨妲?|
|---|---|---|---|
| `snapshot_version` | Integer | **閺?* | 缂佹垵鐣鹃惃鍕彥閻撗呭閺堫剙褰?|
| `export_type` | String | **閺?* | 鐎电厧鍤猾璇茬€? `pptx` / `word` / `package` |
**閸濆秴绨?VO**: `Result<{passed: boolean, warnings: Array, errors: Array}>`

---

## API-48 POST /api/v1/export-tasks

**閸旂喕鍏?*: 缂佹垵鐣炬い鍦窗韫囶偆鍙庨妴浣鼓侀弶璺ㄥ閺堫剙鎷扮€电厧鍤崣鍌涙殶閿涘苯鍨卞鍝勭磽濮濄儱顕遍崙杞版崲閸?

**鐠囬攱鐪版担?(JSON)**
| 鐎涙顔?| 缁鐎?| 韫囧懎锝?| 鐠囧瓨妲?|
|---|---|---|---|
| `project_id` | int | **閺?* | 妞ゅ湱娲癐D |
| `snapshot_version` | Integer | **閺?* | 韫囶偆鍙庨悧鍫熸拱 |
| `export_type` | String | **閺?* | 鐎电厧鍤猾璇茬€? `pptx` / `word` / `package` |
| `config` | String(JSON) | 閸?| 鐎电厧鍤柊宥囩枂閸欏倹鏆?|

**閸氬海顏?DTO**: `ExportTaskDTO { project_id, snapshot_version, export_type, config }`
**閸濆秴绨?VO**: `Result<ExportTaskVO>`

---

## API-49 GET /api/v1/export-tasks

**閸旂喕鍏?*: 閸掑棝銆夐弻銉嚄閺堫兛姹夐幋鏍箯閹哄牊娼堥惃鍕嚤閸戣桨鎹㈤崝?

**閺屻儴顕楅崣鍌涙殶**:
| 鐎涙顔?| 缁鐎?| 韫囧懎锝?| 鐠囧瓨妲?|
|---|---|---|---|
| `status` | String | 閸?| 缁涙盯鈧濮搁幀?|
| `export_type` | String | 閸?| 缁涙盯鈧顕遍崙铏硅閸?|
| `page` | int | 閸?| 姒涙顓? |
| `size` | int | 閸?| 姒涙顓?0 |

**閸濆秴绨?VO**: `Result<PageResult<ExportTaskVO>>`

---

## API-50 GET /api/v1/export-tasks/{id}

**閸旂喕鍏?*: 閺屻儳婀呮潻娑樺閵嗕礁銇戠拹銉ュ斧閸ョ姰鈧浇宸濋柌蹇曞Ц閹礁鎷伴弬鍥︽閻樿埖鈧?

**鐠侯垰绶為崣鍌涙殶**: `id` 閳?鐎电厧鍤禒璇插ID
**閸濆秴绨?VO**: `Result<ExportTaskVO>`

| ExportTaskVO 鐎涙顔?| 缁鐎?| 鐠囧瓨妲?|
|---|---|---|
| `id` | int | 娴犺濮烮D |
| `user_id` | int | 閻劍鍩汭D |
| `project_id` | int | 妞ゅ湱娲癐D |
| `snapshot_version` | Integer | 韫囶偆鍙庨悧鍫熸拱 |
| `export_type` | String | 鐎电厧鍤猾璇茬€?|
| `status` | String | 閻樿埖鈧? `queued`/`generating`/`checking`/`success`/`partial`/`failed`/`cancelled` |
| `config` | String(JSON) | 鐎电厧鍤柊宥囩枂 |
| `file_name` | String | 閺傚洣娆㈤崥?|
| `file_url` | String | 閺傚洣娆RL |
| `file_size` | long | 閺傚洣娆㈡径褍鐨?|
| `download_url` | String | 娑撳娴囬崷鏉挎絻 |
| `url_expire_at` | LocalDateTime | 闁剧偓甯存潻鍥ㄦ埂閺冨爼妫?|
| `file_status` | String | 閺傚洣娆㈤悩鑸碘偓? `available`/`expired`/`cleaned` |
| `quality_report` | String(JSON) | 鐠愩劑鍣洪幎銉ユ啞 |
| `error_msg` | String | 闁挎瑨顕ゆ穱鈩冧紖 |
| `created_at` | LocalDateTime | 閸掓稑缂撻弮鍫曟？ |
| `completed_at` | LocalDateTime | 鐎瑰本鍨氶弮鍫曟？ |

---

## API-51 POST /api/v1/export-tasks/{id}/cancel
**閸旂喕鍏?*: 閸欐牗绉烽幒鎺楁Е娑擃厽鍨ㄩ悽鐔稿灇娑擃厾娈戞禒璇插
**鐠侯垰绶為崣鍌涙殶**: `id` 閳?鐎电厧鍤禒璇插ID
**閸濆秴绨?VO**: `Result<ExportTaskVO>`

---

## API-52 POST /api/v1/export-tasks/{id}/retry
**閸旂喕鍏?*: 閹稿甯箛顐ゅ弾閸滃苯寮弫浼村櫢閺傜増澧界悰?
**鐠侯垰绶為崣鍌涙殶**: `id` 閳?鐎电厧鍤禒璇插ID
**閸濆秴绨?VO**: `Result<ExportTaskVO>`

---

## API-53 GET /api/v1/export-tasks/{id}/quality-report
**閸旂喕鍏?*: 閼惧嘲褰囩€电厧鍤拹銊╁櫤閹躲儱鎲￠妴浣筋劅閸涘﹤鎷伴梽宥囬獓妞?
**鐠侯垰绶為崣鍌涙殶**: `id` 閳?鐎电厧鍤禒璇插ID
**閸濆秴绨?VO**: `Result<{quality_report: String(JSON)}>`

---

## API-54 GET /api/v1/export-artifacts/{id}
**閸旂喕鍏?*: 閼惧嘲褰囬幋鎰亯閺傚洣娆㈤崗鍐╂殶閹诡喓鈧焦鏋冩禒鍓佸Ц閹降鈧胶缂夐悾銉ユ禈濞撳懎宕熼崪灞藉讲妫板嫯顫嶇猾璇茬€?
**鐠侯垰绶為崣鍌涙殶**: `id` 閳?閹存劖鐏夐弬鍥︽ID
**閸濆秴绨?VO**: `Result<ExportTaskVO>`

---

## API-55 POST /api/v1/export-artifacts/{id}/preview-url
**閸旂喕鍏?*: 閻㈢喐鍨氶幋鎰亯缂傗晝鏆愰崶鐐灗妫板嫯顫嶉弬鍥︽閻ㄥ嫮鐓弮鎯邦問闂傤喖婀撮崸鈧?
**鐠侯垰绶為崣鍌涙殶**: `id` 閳?閹存劖鐏夐弬鍥︽ID
**閸濆秴绨?VO**: `Result<{preview_url: String, expires_at: LocalDateTime}>`

---

## API-56 POST /api/v1/export-artifacts/{id}/download-url
**閸旂喕鍏?*: 閻㈢喐鍨氶幋鎰亯閺傚洣娆㈤惃鍕叚閺冩湹绗呮潪浠嬫懠閹?
**鐠侯垰绶為崣鍌涙殶**: `id` 閳?閹存劖鐏夐弬鍥︽ID
**閸濆秴绨?VO**: `Result<{download_url: String, expires_at: LocalDateTime}>`

---

# 娑撳啨鈧胶銇為崠鐑樐侀崸?

## API-57 GET /api/v1/community/items
**閸旂喕鍏?*: 濡偓缁便垹鍙曞鈧崣顖滄暏閻?Skill 閸滃本鏆€鐎涳附顢嶆笟?

**閺屻儴顕楅崣鍌涙殶**:
| 鐎涙顔?| 缁鐎?| 韫囧懎锝?| 鐠囧瓨妲?|
|---|---|---|---|
| `content_type` | String | 閸?| 閸愬懎顔愮猾璇茬€? `skill` / `lesson_case` |
| `subject` | String | 閸?| 鐎涳妇顫?|
| `grade` | String | 閸?| 楠炲楠?|
| `keyword` | String | 閸?| 閸忔娊鏁€涙鎮崇槐?|
| `page` | int | 閸?| 姒涙顓? |
| `size` | int | 閸?| 姒涙顓?0 |

**閸氬海顏?DTO**: `ContentQueryDTO extends PageQuery { content_type, subject, grade, status, keyword }`
**閸濆秴绨?VO**: `Result<PageResult<ContentVO>>`

---

## API-58 GET /api/v1/community/items/{id}
**閸旂喕鍏?*: 閼惧嘲褰囬悽銊┾偓鏂烩偓浣稿綁闁插繈鈧胶銇氭笟瀣ㄢ偓浣风稊閼板懌鈧胶澧楅張顒€鎷伴幒鍫熸綀娣団剝浼?
**鐠侯垰绶為崣鍌涙殶**: `id` 閳?閸愬懎顔怚D
**閸濆秴绨?VO**: `Result<ContentVO>`

| ContentVO 鐎涙顔?| 缁鐎?| 鐠囧瓨妲?|
|---|---|---|
| `id` | int | 閸愬懎顔怚D |
| `content_type` | String | 閸愬懎顔愮猾璇茬€?|
| `author_id` | int | 娴ｆ粏鈧將D |
| `title` | String | 閺嶅洭顣?|
| `description` | String | 閹诲繗鍫?|
| `subject` | String | 鐎涳妇顫?|
| `grade` | String | 楠炲楠?|
| `lesson_type` | String | 鐠囨儳鐎?|
| `content_data` | String(JSON) | 閸愬懎顔愰弫鐗堝祦 |
| `input_variables` | String(JSON) | 鏉堟挸鍙嗛崣姗€鍣?|
| `example_effect` | String | 缁€杞扮伐閺佸牊鐏?|
| `version` | int | 閻楀牊婀伴崣?|
| `version_history` | String(JSON) | 閻楀牊婀伴崢鍡楀蕉 |
| `license` | String | 閹哄牊娼堟穱鈩冧紖 |
| `status` | String | 閻樿埖鈧?|
| `is_top` | int | 閺勵垰鎯佺純顕€銆?|
| `view_count` | int | 濞村繗顫嶉弫?|
| `use_count` | int | 娴ｈ法鏁ら弫?|
| `created_at` | LocalDateTime | 閸掓稑缂撻弮鍫曟？ |
| `updated_at` | LocalDateTime | 閺囧瓨鏌婇弮鍫曟？ |

---

## API-59 PUT /api/v1/community/items/{id}/favorite
**閸旂喕鍏?*: 閺€鎯版閹稿洤鐣剧粈鎯у隘閸愬懎顔?
**鐠侯垰绶為崣鍌涙殶**: `id` 閳?閸愬懎顔怚D
**閸濆秴绨?VO**: `Result<Void>`

---

## API-60 DELETE /api/v1/community/items/{id}/favorite
**閸旂喕鍏?*: 閸欐牗绉烽弨鎯版
**鐠侯垰绶為崣鍌涙殶**: `id` 閳?閸愬懎顔怚D
**閸濆秴绨?VO**: `Result<Void>`

---

## API-61 POST /api/v1/community/items/{id}/view-events
**閸旂喕鍏?*: 鐠佹澘缍嶅ù蹇氼潔娴滃娆㈤敍鍫熷瘻閻劍鍩涢崪灞藉敶鐎圭懓绠撶粵澶嬫纯閺傚府绱?
**鐠侯垰绶為崣鍌涙殶**: `id` 閳?閸愬懎顔怚D
**閸濆秴绨?VO**: `Result<Void>`

---

## API-62 GET /api/v1/community/favorites
**閸旂喕鍏?*: 閸掑棝銆夐弻銉嚄瑜版挸澧犻悽銊﹀煕閺€鎯版閻ㄥ嫬鍙曞鈧崣顖滄暏閸愬懎顔?
**閺屻儴顕楅崣鍌涙殶**: page(姒涙顓?), size(姒涙顓?0)
**閸濆秴绨?VO**: `Result<PageResult<ContentVO>>`

---

## API-63 GET /api/v1/community/recent-views
**閸旂喕鍏?*: 閸掑棝銆夐弻銉嚄瑜版挸澧犻悽銊﹀煕閺堚偓鏉╂垶绁荤憴鍫ｎ唶瑜?
**閺屻儴顕楅崣鍌涙殶**: page(姒涙顓?), size(姒涙顓?0)
**閸濆秴绨?VO**: `Result<PageResult<{item: ContentVO, viewed_at: LocalDateTime}>>`

---

## API-64 DELETE /api/v1/community/recent-views/{itemId}
**閸旂喕鍏?*: 缁夊娅庨幐鍥х暰閺堚偓鏉╂垶绁荤憴鍫ｎ唶瑜?
**鐠侯垰绶為崣鍌涙殶**: `itemId` 閳?閸愬懎顔怚D
**閸濆秴绨?VO**: `Result<Void>`

---

## API-65 POST /api/v1/community/items/{id}/reuse
**閸旂喕鍏?*: 閺嶏繝鐛欓崘鍛啇閻樿埖鈧降鈧胶澧楅張顒€鎷伴幒鍫熸綀閿涘苯顦查崚璺哄煂娑擃亙姹夌粚娲？楠炴儼绻戦崶鐐存烦閻㈢喖銆嶉惄?
**鐠侯垰绶為崣鍌涙殶**: `id` 閳?閸愬懎顔怚D
**鐠囬攱鐪版担?(JSON)**
| 鐎涙顔?| 缁鐎?| 韫囧懎锝?| 鐠囧瓨妲?|
|---|---|---|---|
| `target_version` | Integer | 閸?| 婢跺秶鏁ら幐鍥х暰閻楀牊婀伴敍鍫ョ帛鐠併倖娓堕弬甯礆 |
| `new_project_name` | String | 閸?| 濞插墽鏁撴い鍦窗閸氬秶袨 |
**閸氬海顏?DTO**: `InteractionDTO { action_type, target_type, target_id, target_version, bind_materials }`
**閸濆秴绨?VO**: `Result<ProjectVO>`

---

## API-66 POST /api/v1/community/submissions
**閸旂喕鍏?*: 閸掓稑缂撻幎鏇狀焾閼藉顭?
**鐠囬攱鐪版担?(JSON)**
| 鐎涙顔?| 缁鐎?| 韫囧懎锝?| 鐠囧瓨妲?|
|---|---|---|---|
| `content_type` | String | **閺?* | `skill` / `lesson_case` |
| `title` | String | **閺?* | 閺嶅洭顣?|
| `description` | String | 閸?| 閹诲繗鍫?|
| `subject` | String | 閸?| 鐎涳妇顫?|
| `grade` | String | 閸?| 楠炲楠?|
| `lesson_type` | String | 閸?| 鐠囨儳鐎?|
| `content_data` | String(JSON) | 閸?| 閸愬懎顔愰弫鐗堝祦 |
| `input_variables` | String(JSON) | 閸?| 鏉堟挸鍙嗛崣姗€鍣?|
| `example_effect` | String | 閸?| 缁€杞扮伐閺佸牊鐏?|
| `license` | String | **閺?* | 閹哄牊娼堥崡蹇氼唴 |
**閸氬海顏?DTO**: `ContentDTO { content_type, title, description, subject, grade, lesson_type, content_data, input_variables, example_effect, license }`
**閸濆秴绨?VO**: `Result<ContentVO>`

---

## API-67 GET /api/v1/community/submissions
**閸旂喕鍏?*: 閸掑棝銆夐弻銉嚄瑜版挸澧犻弫娆忕瑎閻ㄥ嫭濮囩粙鍨挤鐎光剝鐗抽悩鑸碘偓?
**閺屻儴顕楅崣鍌涙殶**: status(閸?, page(閸?, size(閸?
**閸氬海顏?DTO**: `ContentQueryDTO extends PageQuery { status }`
**閸濆秴绨?VO**: `Result<PageResult<ContentVO>>`

---

## API-68 GET /api/v1/community/submissions/{id}
**閸旂喕鍏?*: 閼惧嘲褰囬幎鏇狀焾閼藉顭堥妴浣哄閺堫兙鈧礁顓搁弽鍝ュЦ閹礁鎷伴柅鈧崶鐐村壈鐟?
**鐠侯垰绶為崣鍌涙殶**: `id` 閳?閹舵洜顭圛D
**閸濆秴绨?VO**: `Result<ContentVO>`

---

## API-69 PATCH /api/v1/community/submissions/{id}
**閸旂喕鍏?*: 娣囶喗鏁奸懡澶岊焾閹存牠鈧偓閸ョ偘鎱ㄩ弨鍦Ц閹胶娈戦幎鏇狀焾
**鐠侯垰绶為崣鍌涙殶**: `id` 閳?閹舵洜顭圛D
**鐠囬攱鐪版担?*: 娑?API-66 閻╃鎮撶紒鎾寸€敍灞藉弿闁锝?
**閸氬海顏?DTO**: `ContentDTO`
**閸濆秴绨?VO**: `Result<ContentVO>`

---

## API-70 POST /api/v1/community/submissions/{id}/versions
**閸旂喕鍏?*: 娣囨繂鐡ㄩ幎鏇狀焾娑撳秴褰查崣妯煎閺?
**鐠侯垰绶為崣鍌涙殶**: `id` 閳?閹舵洜顭圛D
**鐠囬攱鐪版担?*: description(閸?
**閸濆秴绨?VO**: `Result<{version_id, version_number}>`

---

## API-71 POST /api/v1/community/submissions/{id}/submit
**閸旂喕鍏?*: 閹绘劒姘︾€光剝鐗抽敍鍫ヮ浕閺堢兂VP閻㈠崬濮涢懗钘夌磻閸忓磭顩﹂悽顭掔礆
**鐠侯垰绶為崣鍌涙殶**: `id` 閳?閹舵洜顭圛D
**鐠囬攱鐪版担?(JSON)**
| 鐎涙顔?| 缁鐎?| 韫囧懎锝?| 鐠囧瓨妲?|
|---|---|---|---|
| `source_declaration` | String | **閺?* | 閺夈儲绨竟鐗堟 |
| `notes` | String | 閸?| 鐎光剝鐗虫径鍥ㄦ暈 |
**閸濆秴绨?VO**: `Result<Void>`

---

## API-72 POST /api/v1/community/reports
**閸旂喕鍏?*: 閸掓稑缂撴稉鐐Г鐠佹澘缍?
**鐠囬攱鐪版担?(JSON)**
| 鐎涙顔?| 缁鐎?| 韫囧懎锝?| 鐠囧瓨妲?|
|---|---|---|---|
| `target_type` | String | **閺?* | 娑撶偓濮ょ€电钖勭猾璇茬€?|
| `target_id` | int | **閺?* | 娑撶偓濮ょ€电钖処D |
| `reason` | String | **閺?* | 娑撶偓濮ら崢鐔锋礈 |
| `description` | String | 閸?| 鐠囷妇绮忛幓蹇氬牚 |
**閸氬海顏?DTO**: `AuditDTO { audit_type, target_type, target_id, reason, action, comment }`
**閸濆秴绨?VO**: `Result<{report_id: int}>`

---

## API-73 GET /api/v1/community/reports
**閸旂喕鍏?*: 閸掑棝銆夐弻銉嚄閺堫兛姹夋稉鐐Г閸欏﹤顦╅悶鍡欏Ц閹?
**閺屻儴顕楅崣鍌涙殶**: status(閸?, page(閸?, size(閸?
**閸濆秴绨?VO**: `Result<PageResult<AuditVO>>`

---

## API-74 GET /api/v1/community/reports/{id}
**閸旂喕鍏?*: 閼惧嘲褰囨稉鐐Г閸欐鎮婇悩鑸碘偓浣稿挤婢跺嫮鎮婄紒鎾寸亯
**鐠侯垰绶為崣鍌涙殶**: `id` 閳?娑撶偓濮D
**閸濆秴绨?VO**: `Result<AuditVO>`

---

# 閸忣偁鈧礁鎮楅崣?閳?閻劍鍩涢弶鍐濡€虫健

## API-75 GET /api/v1/admin/users
**閸旂喕鍏?*: 閹稿顫楅懝灞傗偓浣藉閸欓濮搁幀浣告嫲閸忔娊鏁拠宥呭瀻妞ゅ灚鐓＄拠銏㈡暏閹?
**閺屻儴顕楅崣鍌涙殶**: keyword(閸?, user_type(閸?, is_active(閸?, page(姒涙顓?), size(姒涙顓?0)
**閸氬海顏?DTO**: `UserQueryDTO extends PageQuery { keyword, user_type, is_active }`
**閸濆秴绨?VO**: `Result<PageResult<UserVO>>`

---

## API-76 GET /api/v1/admin/users/{id}
**閸旂喕鍏?*: 閼惧嘲褰囬悽銊﹀煕閻樿埖鈧降鈧浇顫楅懝灞傗偓浣规綀闂勬劖鎲崇憰浣稿挤鐎瑰鍙忛悩鑸碘偓?
**鐠侯垰绶為崣鍌涙殶**: `id` 閳?閻劍鍩汭D
**閸濆秴绨?VO**: `Result<UserVO>`

---

## API-77 PATCH /api/v1/admin/users/{id}/status
**閸旂喕鍏?*: 閸氼垳鏁ら妴浣镐粻閻劍鍨ㄩ柨浣哥暰閻劍鍩涚拹锕€褰?
**鐠侯垰绶為崣鍌涙殶**: `id` 閳?閻劍鍩汭D
**鐠囬攱鐪版担?(JSON)**
| 鐎涙顔?| 缁鐎?| 韫囧懎锝?| 鐠囧瓨妲?|
|---|---|---|---|
| `is_active` | int | **閺?* | 0=閸嬫粎鏁? 1=閸氼垳鏁? -1=闁夸礁鐣?|
**閸濆秴绨?VO**: `Result<UserVO>`

---

## API-78 POST /api/v1/admin/users
**閸旂喕鍏?*: 閸掓稑缂撻崡鏇氶嚋閸氬骸褰寸拹锕€褰?
**鐠囬攱鐪版担?(JSON)**
| 鐎涙顔?| 缁鐎?| 韫囧懎锝?| 鐠囧瓨妲?|
|---|---|---|---|
| `username` | String | **閺?* | 閻劍鍩涢崥?|
| `password` | String | **閺?* | 鐎靛棛鐖滈敍鍫濆缁旑垯绱堕弰搴㈡瀮閿涘苯鎮楃粩顖氭惐鐢苯鎮楃€涙ê鍋嶉敍?|
| `real_name` | String | **閺?* | 閻喎鐤勬慨鎾虫倳 |
| `phone` | String | 閸?| 閹靛婧€閸?|
| `email` | String | 閸?| 闁喚顔?|
| `user_type` | String | **閺?* | `admin` |
| `roles` | String(JSON) | **閺?* | 鐟欐帟澹婇崚妤勩€?|
**閸氬海顏?DTO**: `UserDTO { username, password, real_name, phone, email, avatar, user_type, roles, permissions, is_active }`
**閸濆秴绨?VO**: `Result<UserVO>`

---

## API-79 POST /api/v1/admin/users/batch
**閸旂喕鍏?*: 閹靛綊鍣洪崚娑樼紦閸氬骸褰寸拹锕€褰?
**鐠囬攱鐪版担?(JSON)**
| 鐎涙顔?| 缁鐎?| 韫囧懎锝?| 鐠囧瓨妲?|
|---|---|---|---|
| `idempotent_key` | String | **閺?* | 楠炲倻鐡戦柨?|
| `users` | Array | **閺?* | 閻劍鍩涢崚妤勩€冮敍鍫熺槨娑擃亜鎮揂PI-78缂佹挻鐎敍灞界槕閻椒绱堕弰搴㈡瀮閿涘苯鎮楃粩顖氭惐鐢苯鎮楃€涙ê鍋嶉敍?|
**閸濆秴绨?VO**: `Result<{results: Array<{username, success, initial_credentials, error}>>}`

---

## API-80 GET /api/v1/admin/roles
**閸旂喕鍏?*: 閺屻儴顕楅崥搴″酱鐟欐帟澹婇妴浣规綀闂勬劙娉﹂崥鍫濆挤鐎光剝鐗抽懠鍐ㄦ纯
**閸濆秴绨?VO**: `Result<Array<{role_id, role_name, permissions, audit_scope}>>`

---

## API-81 PUT /api/v1/admin/users/{id}/roles
**閸旂喕鍏?*: 閸掑棝鍘ょ化鑽ょ埠缁狅紕鎮婇崨妯诲灗閸愬懎顔愮€光剝鐗抽崨妯款潡閼?
**鐠侯垰绶為崣鍌涙殶**: `id` 閳?閻劍鍩汭D
**鐠囬攱鐪版担?(JSON)**: `roles`(String JSON) **閺?*
**閸濆秴绨?VO**: `Result<UserVO>`

---

## API-82 PUT /api/v1/admin/roles/{id}/permissions
**閸旂喕鍏?*: 闁板秶鐤嗛崥搴″酱閸旂喕鍏橀弶鍐閸欏﹤顓搁弽姝屽瘱閸?
**鐠侯垰绶為崣鍌涙殶**: `id` 閳?鐟欐帟澹奍D
**鐠囬攱鐪版担?(JSON)**: `permissions`(String JSON) **閺?*
**閸濆秴绨?VO**: `Result<Void>`

---

# 娑旀縿鈧礁鎮楅崣?閳?閸忣剙鍙＄挧鍕爱濡€虫健

## API-83 GET /api/v1/admin/public-resources
**閸旂喕鍏?*: 閸掑棝銆夐弻銉嚄閸忣剙鍙＄挧鍕爱
**閺屻儴顕楅崣鍌涙殶**: resource_type(閸?, status(閸?, page(姒涙顓?), size(姒涙顓?0)
**閸濆秴绨?VO**: `Result<PageResult<ResourceVO>>`

| ResourceVO 鐎涙顔?| 缁鐎?| 鐠囧瓨妲?|
|---|---|---|
| `id` | int | 鐠у嫭绨甀D |
| `resource_type` | String | 鐠у嫭绨猾璇茬€?|
| `title` | String | 閺嶅洭顣?|
| `subject` | String | 鐎涳妇顫?|
| `grade` | String | 楠炲楠?|
| `file_url` | String | 閺傚洣娆RL |
| `template_data` | String(JSON) | 濡剝婢橀弫鐗堝祦 |
| `thumbnail` | String | 缂傗晝鏆愰崶?|
| `description` | String | 閹诲繗鍫?|
| `status` | int | 閻樿埖鈧?|
| `uploaded_by` | Integer | 娑撳﹣绱堕懓鍖 |
| `created_at` | LocalDateTime | 閸掓稑缂撻弮鍫曟？ |
| `updated_at` | LocalDateTime | 閺囧瓨鏌婇弮鍫曟？ |

---

## API-84 POST /api/v1/admin/public-resources/uploads
**閸旂喕鍏?*: 閸掓稑缂撻崗顒€鍙＄挧鍕爱娑撳﹣绱舵导姘崇樈
**鐠囬攱鐪版担?(JSON)**: resource_type(**閺?*), title(**閺?*), file_url(**閺?*), file_size(**閺?*)
**閸氬海顏?DTO**: `ResourceDTO { resource_type, title, subject, grade, file_url, template_data, thumbnail, description, status }`
**閸濆秴绨?VO**: `Result<{upload_id, upload_url, expires_at}>`

---

## API-85 POST /api/v1/admin/public-resources/uploads/{id}/complete
**閸旂喕鍏?*: 鐎瑰本鍨氭稉濠佺炊楠炴儼袝閸欐垵鐣ㄩ崗銊︻梾濞?
**鐠侯垰绶為崣鍌涙殶**: `id` 閳?娑撳﹣绱舵导姘崇樈ID
**閸濆秴绨?VO**: `Result<ResourceVO>`

---

## API-86 GET /api/v1/admin/public-resources/{id}
**閸旂喕鍏?*: 閼惧嘲褰囬崗顒€鍙＄挧鍕爱鐠囷附鍎?
**鐠侯垰绶為崣鍌涙殶**: `id` 閳?鐠у嫭绨甀D
**閸濆秴绨?VO**: `Result<ResourceVO>`

---

## API-87 PATCH /api/v1/admin/public-resources/{id}
**閸旂喕鍏?*: 閺囧瓨鏌婇崗顒€鍙＄挧鍕爱閸忓啯鏆熼幑?
**鐠侯垰绶為崣鍌涙殶**: `id` 閳?鐠у嫭绨甀D
**鐠囬攱鐪版担?*: title(閸?, subject(閸?, grade(閸?, description(閸?
**閸氬海顏?DTO**: `ResourceDTO`
**閸濆秴绨?VO**: `Result<ResourceVO>`

---

## API-88 PUT /api/v1/admin/public-resources/{id}/status
**閸旂喕鍏?*: 閸氼垳鏁?閸嬫粎鏁ら崗顒€鍙＄挧鍕爱
**鐠侯垰绶為崣鍌涙殶**: `id` 閳?鐠у嫭绨甀D
**鐠囬攱鐪版担?*: status(int) **閺?* 0=閸嬫粎鏁?1=閸氼垳鏁?
**閸濆秴绨?VO**: `Result<ResourceVO>`

---

## API-89 GET /api/v1/admin/public-resources/{id}/processing-status
**閸旂喕鍏?*: 閺屻儴顕楁径鍕倞閻樿埖鈧?
**鐠侯垰绶為崣鍌涙殶**: `id` 閳?鐠у嫭绨甀D
**閸濆秴绨?VO**: `Result<{security_check, parse_status, index_status, error_msg}>`

---

# 閸椾降鈧礁鎮楅崣?閳?閸愬懎顔愮€光剝鐗虫稉搴濆閹躲儱顦╅悶?

## API-90 GET /api/v1/admin/moderation/tasks
**閸旂喕鍏?*: 閹稿濮搁幀浣碘偓浣割嚠鐠烇紕琚崹瀣嫲鐎光剝鐗抽崨妯荤叀鐠囥垹顓搁弽闀愭崲閸?
**閺屻儴顕楅崣鍌涙殶**: status(閸?, target_type(閸?, handler_id(閸?, page(姒涙顓?), size(姒涙顓?0)
**閸濆秴绨?VO**: `Result<PageResult<AuditVO>>`

---

## API-91 GET /api/v1/admin/moderation/tasks/{id}
**閸旂喕鍏?*: 閼惧嘲褰囧鍛吀閸愬懎顔愰妴浣瑰缁嬪じ姹夐妴浣规降濠ф劗澧楅張顑锯偓浣瑰房閺夊啩淇婇幁顖氭嫲濡偓濞村绮ㄩ弸?
**鐠侯垰绶為崣鍌涙殶**: `id` 閳?鐎光剝鐗虫禒璇插ID
**閸濆秴绨?VO**: `Result<AuditVO>`

---

## API-92 POST /api/v1/admin/moderation/tasks/{id}/decisions
**閸旂喕鍏?*: 閹绘劒姘︾€光剝鐗抽崘鍐茬暰
**鐠侯垰绶為崣鍌涙殶**: `id` 閳?鐎光剝鐗虫禒璇插ID
**鐠囬攱鐪版担?(JSON)**
| 鐎涙顔?| 缁鐎?| 韫囧懎锝?| 鐠囧瓨妲?|
|---|---|---|---|
| `action` | String | **閺?* | `approve` / `reject` / `rework` |
| `comment` | String | 閸?| 鐎光剝鐗抽幇蹇氼潌 |
**閸氬海顏?DTO**: `AuditDTO { audit_type, target_type, target_id, reason, action, comment }`
**閸濆秴绨?VO**: `Result<Void>`

---

## API-93 PUT /api/v1/admin/community-items/{id}/status
**閸旂喕鍏?*: 娑撳﹥鐏?娑撳鐏?閸嬫粎鏁ょ粈鎯у隘閸愬懎顔?
**鐠侯垰绶為崣鍌涙殶**: `id` 閳?缁€鎯у隘閸愬懎顔怚D
**鐠囬攱鐪版担?*: status(String) **閺?* `published`/`unpublished`/`disabled`
**閸濆秴绨?VO**: `Result<ContentVO>`

---

## API-94 PUT /api/v1/admin/community-items/{id}/recommendation
**閸旂喕鍏?*: 鐠佸墽鐤嗛幒銊ㄥ礃閹存牜鐤嗘い?
**鐠侯垰绶為崣鍌涙殶**: `id` 閳?缁€鎯у隘閸愬懎顔怚D
**鐠囬攱鐪版担?(JSON)**
| 鐎涙顔?| 缁鐎?| 韫囧懎锝?| 鐠囧瓨妲?|
|---|---|---|---|
| `is_top` | int | **閺?* | 0=閸欐牗绉? 1=閹恒劏宕? 2=缂冾噣銆?|
| `expires_at` | LocalDateTime | 閸?| 閸掔増婀￠弮鍫曟？ |
**閸濆秴绨?VO**: `Result<ContentVO>`

---

## API-95 GET /api/v1/admin/reports
**閸旂喕鍏?*: 閸掑棝銆夐弻銉嚄娑撶偓濮?
**閺屻儴顕楅崣鍌涙殶**: status(閸?: `pending`/`processing`/`resolved`, page(閸?, size(閸?
**閸濆秴绨?VO**: `Result<PageResult<AuditVO>>`

---

## API-96 GET /api/v1/admin/reports/{id}
**閸旂喕鍏?*: 閺屻儳婀呮稉鐐Г鐠囷附鍎?
**鐠侯垰绶為崣鍌涙殶**: `id` 閳?娑撶偓濮D
**閸濆秴绨?VO**: `Result<AuditVO>`

---

## API-97 POST /api/v1/admin/reports/{id}/resolution
**閸旂喕鍏?*: 閹绘劒姘︽稉鐐Г婢跺嫮鎮婄紒鎾诡啈
**鐠侯垰绶為崣鍌涙殶**: `id` 閳?娑撶偓濮D
**鐠囬攱鐪版担?(JSON)**
| 鐎涙顔?| 缁鐎?| 韫囧懎锝?| 鐠囧瓨妲?|
|---|---|---|---|
| `action` | String | **閺?* | `dismiss`/`warn`/`remove`/`ban` |
| `comment` | String | 閸?| 婢跺嫮鎮婄拠瀛樻 |
**閸氬海顏?DTO**: `AuditDTO`
**閸濆秴绨?VO**: `Result<Void>`

---

# 閸椾椒绔撮妴浣告倵閸?閳?鐎电厧鍤Ο鈩冩緲濡€虫健

## API-98 GET /api/v1/admin/export-templates
**閸旂喕鍏?*: 閸掑棝銆夐弻銉嚄鐎电厧鍤Ο鈩冩緲
**閺屻儴顕楅崣鍌涙殶**: export_type(閸?, status(閸?, page(閸?, size(閸?
**閸濆秴绨?VO**: `Result<PageResult<{id, name, export_type, version, status, created_at, updated_at}>>`

---

## API-99 POST /api/v1/admin/export-templates
**閸旂喕鍏?*: 閸掓稑缂撶€电厧鍤Ο鈩冩緲閸欏﹪顩绘稉顏嗗閺?
**鐠囬攱鐪版担?(JSON)**: name(**閺?*), export_type(**閺?*), template_data(**閺?*), description(閸?
**閸濆秴绨?VO**: `Result<{id, version}>`

---

## API-100 PATCH /api/v1/admin/export-templates/{id}
**閸旂喕鍏?*: 閺囧瓨鏌婂Ο鈩冩緲閸忓啯鏆熼幑顔藉灗閸掓稑缂撻弬鎵閺?
**鐠侯垰绶為崣鍌涙殶**: `id` 閳?濡剝婢業D
**鐠囬攱鐪版担?*: name(閸?, template_data(閸?, description(閸?
**閸濆秴绨?VO**: `Result<{id, version}>`

---

## API-101 PUT /api/v1/admin/export-templates/{id}/status
**閸旂喕鍏?*: 閸欐垵绔烽幋鏍т粻閻劍膩閺夎法澧楅張?
**鐠侯垰绶為崣鍌涙殶**: `id` 閳?濡剝婢業D
**鐠囬攱鐪版担?*: status(String) **閺?* `published`/`unpublished`
**閸濆秴绨?VO**: `Result<Void>`

---

# 閸椾椒绨╅妴浣告倵閸?閳?AI闁板秶鐤嗗Ο鈥虫健

## API-102 GET /api/v1/admin/ai-configs
**閸旂喕鍏?*: 閺屻儴顕楀Ο鈥崇€烽妴浣镐紣閸忓嘲鎷版潻鎰攽閸欏倹鏆熼柊宥囩枂
**閺屻儴顕楅崣鍌涙殶**: config_group(閸?
**閸濆秴绨?VO**: `Result<Array<ConfigVO>>`

| ConfigVO 鐎涙顔?| 缁鐎?| 鐠囧瓨妲?|
|---|---|---|
| `id` | int | 闁板秶鐤咺D |
| `config_group` | String | 閸掑棛绮? `ai_model`/`platform`/`security`/`template`/`sensitive_word` |
| `config_key` | String | 闁板秶鐤嗛柨?|
| `config_value` | String | 闁板秶鐤嗛崐?|
| `description` | String | 閹诲繗鍫?|
| `updated_by` | Integer | 閺囧瓨鏌婃禍?|
| `updated_at` | LocalDateTime | 閺囧瓨鏌婇弮鍫曟？ |

---

## API-103 POST /api/v1/admin/ai-configs
**閸旂喕鍏?*: 閸掓稑缂揂I闁板秶鐤嗛悧鍫熸拱
**鐠囬攱鐪版担?(JSON)**: config_group(**閺?*), config_key(**閺?*), config_value(**閺?*), description(閸?
**閸氬海顏?DTO**: `ConfigDTO { config_group, config_key, config_value, description }`
**閸濆秴绨?VO**: `Result<ConfigVO>`

---

## API-120 POST /api/v1/admin/ai-configs/{id}/publish
**閸旂喕鍏?*: 閸欐垵绔稟I闁板秶鐤嗛悧鍫熸拱
**鐠侯垰绶為崣鍌涙殶**: `id` 閳?闁板秶鐤咺D
**閸濆秴绨?VO**: `Result<{node_status: Array<{node, status}>>}`

---

## API-121 POST /api/v1/admin/ai-configs/{id}/rollback
**閸旂喕鍏?*: 閸ョ偞绮撮崚鐗堝瘹鐎规艾宸婚崣鏌ュ帳缂?
**鐠侯垰绶為崣鍌涙殶**: `id` 閳?闁板秶鐤咺D
**鐠囬攱鐪版担?(JSON)**: target_version(int **閺?*), reason(String **閺?*)
**閸濆秴绨?VO**: `Result<ConfigVO>`

---

# 閸椾椒绗侀妴浣告倵閸?閳?鐎瑰鍙忕粵鏍殣

## API-122 GET /api/v1/admin/security-policies
**閸旂喕鍏?*: 閼惧嘲褰囩€瑰鍙忕粵鏍殣閸欏﹤缍嬮崜宥囨晸閺佸牏澧楅張?
**閸濆秴绨?VO**: `Result<Array<ConfigVO>>`

---

## API-123 PUT /api/v1/admin/security-policies/{id}
**閸旂喕鍏?*: 閺囧瓨鏌婄€瑰鍙忕粵鏍殣閿涘牏澧楅張顒€褰块梼鎻掕嫙閸欐垼顩惄鏍电礆
**鐠侯垰绶為崣鍌涙殶**: `id` 閳?缁涙牜鏆怚D
**鐠囬攱鐪版担?(JSON)**: config_value(**閺?*), version(int **閺?*)
**閸氬海顏?DTO**: `ConfigDTO`
**閸濆秴绨?VO**: `Result<ConfigVO>`

---

## API-124 POST /api/v1/admin/security-policies/{id}/publish
**閸旂喕鍏?*: 閸欐垵绔风€瑰鍙忕粵鏍殣
**鐠侯垰绶為崣鍌涙殶**: `id` 閳?缁涙牜鏆怚D
**閸濆秴绨?VO**: `Result<{published: boolean}>`

---

# 閸椾礁娲撻妴浣告倵閸?閳?閺冦儱绻旀稉搴ｆ箙閺?

## API-125 GET /api/v1/admin/audit-logs
**閸旂喕鍏?*: 閺屻儴顕楅懘杈ㄦ櫛閸氬海娈戞稉姘鐎孤ゎ吀閺冦儱绻?
**閺屻儴顕楅崣鍌涙殶**: user_id(閸?, log_type(閸?, module(閸?, start_time(閸?, end_time(閸?, page(姒涙顓?), size(姒涙顓?0)
**閸氬海顏?DTO**: `LogQueryDTO extends PageQuery { user_id, log_type, module, start_time, end_time }`
**閸濆秴绨?VO**: `Result<PageResult<LogVO>>`

| LogVO 鐎涙顔?| 缁鐎?| 鐠囧瓨妲?|
|---|---|---|
| `id` | long | 閺冦儱绻擨D |
| `user_id` | Integer | 閹垮秳缍旈懓鍖 |
| `log_type` | String | 閺冦儱绻旂猾璇茬€? `operation`/`download`/`browse`/`audit` |
| `module` | String | 閹碘偓鐏炵偞膩閸?|
| `action` | String | 閹垮秳缍旈崝銊ょ稊 |
| `target_type` | String | 閻╊喗鐖ｇ猾璇茬€?|
| `target_id` | Integer | 閻╊喗鐖D |
| `detail` | String(JSON) | 鐠囷妇绮忔穱鈩冧紖 |
| `ip` | String | IP閸︽澘娼?|
| `created_at` | LocalDateTime | 閸掓稑缂撻弮鍫曟？ |

---

## API-126 GET /api/v1/admin/system-logs
**閸旂喕鍏?*: 閺屻儴顕楅懘杈ㄦ櫛閸氬海娈戠化鑽ょ埠鏉╂劘顢戦崣濠傜磽鐢憡妫╄箛?
**閺屻儴顕楅崣鍌涙殶**: log_type(閸?, module(閸?, start_time(閸?, end_time(閸?, page(姒涙顓?), size(姒涙顓?0)
**閸氬海顏?DTO**: `LogQueryDTO`
**閸濆秴绨?VO**: `Result<PageResult<LogVO>>`

---

## API-127 GET /api/v1/admin/dashboard
**閸旂喕鍏?*: 閺屻儴顕楁稉姘閹稿洦鐖?
**閸濆秴绨?VO**: `Result<{user_count, resource_count, ai_task_count, export_task_count, moderation_pending_count}>`

---

## API-128 GET /api/v1/admin/alerts
**閸旂喕鍏?*: 閸掑棝銆夐弻銉嚄閸涘﹨顒?
**閺屻儴顕楅崣鍌涙殶**: level(閸?, source(閸?, status(閸?, page(姒涙顓?), size(姒涙顓?0)
**閸濆秴绨?VO**: `Result<PageResult<{id, level, source, title, status, created_at, resolved_at}>>`

---

## API-129 GET /api/v1/admin/alerts/{id}
**閸旂喕鍏?*: 閼惧嘲褰囬崨濠咁劅鐠囷附鍎?
**鐠侯垰绶為崣鍌涙殶**: `id` 閳?閸涘﹨顒烮D
**閸濆秴绨?VO**: `Result<{id, level, source, title, detail, status, acknowledged_by, resolved_by, created_at, acknowledged_at, resolved_at}>`

---

## API-130 POST /api/v1/admin/alerts/{id}/acknowledge
**閸旂喕鍏?*: 绾喛顓婚崨濠咁劅
**鐠侯垰绶為崣鍌涙殶**: `id` 閳?閸涘﹨顒烮D
**閸濆秴绨?VO**: `Result<Void>`

---

## API-131 POST /api/v1/admin/alerts/{id}/resolve
**閸旂喕鍏?*: 鐟欙絽鍠呴崨濠咁劅
**鐠侯垰绶為崣鍌涙殶**: `id` 閳?閸涘﹨顒烮D
**鐠囬攱鐪版担?*: resolution(String **閺?*)
**閸濆秴绨?VO**: `Result<Void>`

---

# 闂勫嫬缍? 缂佺喍绔撮崫宥呯安缂佹挻鐎?

### Result閿涘牓鈧氨鏁ら崫宥呯安閿?
```json
{
  "code": 200,
  "message": "success",
  "data": { ... }
}
```
| 鐎涙顔?| 缁鐎?| 鐠囧瓨妲?|
|---|---|---|
| `code` | int | 200閹存劕濮涢敍灞藉従娴犳牔璐熼柨娆掝嚖閻?|
| `message` | String | 閹诲繗鍫穱鈩冧紖 |
| `data` | T | 閺佺増宓佹担鎿勭礄缁鐎风憴浣告倗API鐠囧瓨妲戦敍?|

### PageResult閿涘牆鍨庢い闈涙惙鎼存棑绱?
```json
{
  "total": 100,
  "page": 1,
  "size": 10,
  "records": [ ... ]
}
```
| 鐎涙顔?| 缁鐎?| 鐠囧瓨妲?|
|---|---|---|
| `total` | long | 閹槒顔囪ぐ鏇熸殶 |
| `page` | int | 瑜版挸澧犳い鐢电垳 |
| `size` | int | 濮ｅ繘銆夐弶鈩冩殶 |
| `records` | List<T> | 瑜版挸澧犳い鍨殶閹诡喖鍨悰?|

---

# 闂勫嫬缍? 鐢瓕顫?HTTP 閻樿埖鈧胶鐖?

| 閻樿埖鈧胶鐖?| 鐠囧瓨妲?|
|---|---|
| 200 | 鐠囬攱鐪伴幋鎰 |
| 400 | 鐠囬攱鐪伴崣鍌涙殶闁挎瑨顕?|
| 401 | 閺堫亣顓荤拠?/ Token 閺冪姵鏅?|
| 403 | 閺冪姵娼堥梽鎰問闂?|
| 404 | 鐠у嫭绨稉宥呯摠閸?|
| 409 | 閻楀牊婀伴崘鑼崐閿涘牅绠扮憴鍌炴敚閿?|
| 422 | 娑撴艾濮熼弽锟犵崣娑撳秹鈧俺绻?|
| 429 | 鐠囬攱鐪版０鎴犲芳闂勬劕鍩?|
| 500 | 閺堝秴濮熼崳銊ュ敶闁劑鏁婄拠?|

---

# 闂勫嫬缍? 閸忋劌鐪拠閿嬬湴婢?

| 鐠囬攱鐪版径?| 韫囧懎锝?| 鐠囧瓨妲?|
|---|---|---|
| `Authorization` | 闂団偓鐠併倛鐦夐惃鍕复閸欙絽绻€婵?| `Bearer <token>` |
| `Content-Type` | POST/PATCH/PUT 韫囧懎锝?| `application/json` |
| `Idempotent-Key` | 楠炲倻鐡戦弫蹇斿妳閹垮秳缍旈崣顖炩偓?| 闂冩煡鍣告径宥嗗絹娴?|
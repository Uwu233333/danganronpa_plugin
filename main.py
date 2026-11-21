from __future__ import annotations
import asyncio, json, random, re, sqlite3, time, traceback, shutil
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from astrbot.api.event import filter, AstrMessageEvent, MessageChain
from astrbot.api.star import Context, Star
from astrbot.api import AstrBotConfig, logger
from astrbot.core.utils.astrbot_path import get_astrbot_data_path

ROOT = Path(__file__).parent
MENU_IMAGE = ROOT / 'assets' / 'student_handbook_menu.png'
PLUGIN_DATA = Path(get_astrbot_data_path()) / 'plugin_data' / 'danganronpa_simulator'
BACKUP_DIR = PLUGIN_DATA / 'backups'
DB = PLUGIN_DATA / 'danganronpa.sqlite3'
LEGACY_DB = ROOT / 'data' / 'danganronpa.sqlite3'

# Bundled starter roster. Character data is deliberately kept separate by title.
ROSTERS = {
 'dr1': ['苗木诚','舞园沙耶香','桑田怜恩','雾切响子','十神白夜','山田一二三','大和田纹土','塞蕾丝缇雅·罗登贝克','腐川冬子','朝日奈葵','石丸清多夏','大神樱','叶隐康比吕','江之岛盾子','不二咲千寻','战刃骸'],
 'dr2': ['日向创','狛枝凪斗','七海千秋','田中眼蛇梦','左右田和一','索尼娅·内瓦曼','九头龙冬彦','边古山佩子','终里赤音','弐大猫丸','花村辉辉','小泉真昼','西园寺日寄子','澪田唯吹','罪木蜜柑','伪十神白夜'],
 'v3': ['赤松枫','最原终一','王马小吉','百田解斗','春川魔姬','梦野秘密子','茶柱转子','入间美兔','天海兰太郎','东条斩美','星龙马','真宫寺是清','白银紬','夜长安吉','狱原钢太郎','Kiibo']
}
WORLD_NAMES = {'dr1':'弹丸论破1','dr2':'超级弹丸论破2','v3':'新弹丸论破V3'}

# Canon gift catalogs: only entries supplied for each title are included.
GIFT_CATALOG = {
 'dr1': {
  1:'矿泉水',2:'可乐可乐',3:'猫屎咖啡',4:'玫瑰果香茶',5:'盐',6:'薯片',7:'七彩面包干',8:'焦黑牛角包',9:'神速杯面',10:'华丽的王子殿下',
  11:'军粮',12:'泳圈甜甜圈',13:'很一般的便当',14:'葵瓜子',15:'鸟食',16:'小猫发夹',17:'永恒手链',18:'恋爱传说戒指',19:'鹤龟钻戒',20:'希望之峰戒指',
  21:'蓝莓香水',22:'圣甲虫胸针',23:'武神护符',24:'明日的拳套',25:'脑门眼镜',26:'G-SICK',27:'滚轴拖鞋',28:'红色的围巾',29:'叶片兜裆布',30:'特鲁猫的灯笼裤',
  31:'小白兔耳罩',32:'新品缠腰布',33:'穴户YASU的T恤',34:'支配着丁字裤',35:'手型罩',36:'水之恋人',37:'糯糯公主的手办',38:'收音机君玩偶',39:'理发剪刀',40:'有缝剪刀',
  41:'高级灰鼠皮草沙发套',42:'基尔里安照相机',43:'反应搞笑艺术珍藏集',44:'风滚草团',45:'无限蒲公英',46:'试管玫瑰',47:'樱花花束',49:'残铁剑',50:'村正',51:'激光枪兹利安',52:'黄金枪',53:'狂战士铠甲',54:'自动销毁盒式录音带',55:'无言电话',
  56:'毛虫君',57:'昭和收音机',58:'速球大臣',59:'古董洋娃娃',60:'水晶骷髅',61:'黄金宇宙飞船',62:'圣德太子的地球仪',63:'月亮石',64:'阿修罗之泪',65:'Omoplata的秘笈',66:'百万美金悬赏问题',67:'掌机',68:'丧尸计划',69:'异端之舞',70:'Tips & Tips',
  71:'少女的手提包',72:'小芥子发电机',73:'第二颗纽扣',74:'某人的毕业相册',75:'台虎钳',76:'玉串',77:'浮石',78:'糯米纸',79:'水笛',80:'BOJOBO许愿娃娃',81:'微型灯',82:'蝴蝶领结变声器',83:'古代旅行券',84:'小说家的钢笔',86:'猫狗杂志',87:'陨石之箭',88:'下巴钻头',89:'绿色的玩偶服',90:'红色的玩偶服'
 },
 'dr2': {
  1:'矿泉水',2:'弹珠汽水',3:'椰子汁',4:'蓝羊（逆能量饮料）',5:'猫屎咖啡',6:'肉桂茶',7:'无酒精葡萄酒',8:'麦饭包',9:'巧克力肉干',10:'明太法国面包',
  11:'奶油圆蛋糕',12:'希望的干面包',13:'点心面包袋',14:'炸薯片',15:'刨冰',16:'贾巴天然盐',17:'椰肉刺身',18:'葵瓜子',19:'椰子果实',20:'伊吕波T恤',
  21:'纯色牛仔裤',22:'连衫围裙',23:'毛皮围巾',24:'全新的裹胸布',25:'女王的拘束衣',26:'间谍鞋钉',27:'秘密靴',28:'半分安全鞋',29:'烦恼眼镜',30:'蓝莓纯金',
  31:'破邪的耳环',32:'银制戒指',33:'希望之峰戒指',34:'幽灵戒指',35:'包裹布套装',36:'Another Hope',37:'贾巴沃克岛式挂坠',38:'疾驱守扇子',39:'无处不在的手帐',40:'千年悬赏问题',
  41:'超技林第二版',42:'大神宗家之书',43:"Men's Manma",44:'接吻笔记',45:'黑兔子读本',46:'2.5D耳机',47:'无线电探测器',48:'震动量筒',49:'情趣烧瓶',50:'激光饭煲HG',
  51:'红外线式体温计',52:'消焰器',53:'李林塔尔之翼',54:'基尔里安照相机',55:'Mr.订书机',56:'小型核融炉',57:'多面骰子组合',58:'家用机',59:'掌机',60:'American Cracker',
  61:'玩具相机',62:'手套游戏摇杆',63:'美索不达米亚',64:'硝基驱动',65:'啪啪卷',66:'搞笑球',67:'可动木偶',68:'围棋棋子',69:'瓶中信',70:'昭和收音机',
  71:'古董人偶',72:'第二颗纽扣',73:'月之石',74:'不战的仁义',75:'自暴自弃',76:'千本樱影好',77:'怀纸“十幕目诗录”',78:'深海之血',79:'莳绘竹刀',80:'迷你消波块',
  81:'星之砂',82:'日式茶杯',83:'表里四弦琴',84:'圆珠笔杆',85:'BOJOBO许愿娃娃',86:'百年薰花',87:'绝对音叉',88:'七支刀',89:'神砂岚之角',90:'记忆笔记',
  91:'战刃小刀',92:'坏掉的导弹',93:'带着小熊头饰的少女',94:'铁撬',95:'蘸水笔',96:'纸巾',97:'贾巴之蛙',98:'女孩蜥蜴',99:'钝菜刀',100:'灵异相框',101:'濡雪月花',102:'试管玫瑰'
 },
 'v3': {
  1:'乌龙茶',2:'珍珠果汁',3:'姜茶',4:'克利奥帕特拉的珍珠',5:'不死酒FREE',6:'西红柿酱',7:'砂糖',8:'橄榄油',9:'太空蛋糕',10:'气球炸弹泡泡糖',11:'枫糖法奇',12:'脱水牛奶',13:'兔子苹果',14:'超硬冰淇淋',15:'寿喜烧牛奶糖',16:'薄荷香烟糖',17:'像某人脸的饺子',20:'条纹领带',23:'运动衣',25:'秋色披肩',26:'手织毛衣',27:'应援团长的长外套',28:'指甲油刷',29:'可穿式厚被',30:'贝雷帽',32:'袖扣',36:'哈姆的心情',38:'修成正果☆咒语全集',39:'榻上故事',40:'少年清凉志',41:'快乐动物园',42:'最新零件目录'
 }
}
GIFT_NAME_TO_ID = {w:{name:i for i,name in items.items()} for w,items in GIFT_CATALOG.items()}
# Verified preference data, keyed by in-game gift number. Unlisted gifts stay neutral;
# this avoids inventing likes/dislikes where a source does not establish them.
GIFT_PREFS = {
 'dr1': {
  '山田一二三':{'love':[2,6,37]}, '十神白夜':{'love':[3,22,52,57,60,61,62,66,69]},
  '雾切响子':{'love':[3,21,46,47,80]}, '塞蕾丝缇雅·罗登贝克':{'love':[4,18,19,59]},
  '大和田纹土':{'love':[9,27,32,41]}, '江之岛盾子':{'love':[11,16,46,61]},
  '朝日奈葵':{'love':[12,16,26,36,38]}, '舞园沙耶香':{'love':[16,17,18,46,47]},
  '桑田怜恩':{'love':[17,21,33,68]}, '腐川冬子':{'love':[17,25,46,47,59,71,84]},
  '不二咲千寻':{'love':[21,42,45,70]}, '大神樱':{'love':[23,32,46,64,65]},
  '石丸清多夏':{'love':[24,28,43,88]}, '叶隐康比吕':{'love':[60,61,62,76,87]}
 },
 'dr2': {
  '狛枝凪斗':{'love':[33,90,91],'like':[4,12,15,31,36,68,86,110],'dislike':[112],'hate':[34,66,93]},
  '伪十神白夜':{'love':[9,13,17,45],'like':[2,8,10,11,12,14,18,19,30,33,43,50,68,78,81,85,86,102],'dislike':[4,6,20,21,22,23,24,25,26,27,28,34,36,47,52,56,66,70,73,90,92,112],'hate':[5,40,67,76,88,91,99]},
  '田中眼蛇梦':{'love':[18,31,56],'like':[4,23,33,34,36,38,62,73,76,77,81,86,87,88,89,97,98,103],'dislike':[20,21,22,29,66,112],'hate':[44,48,49,67]},
  '左右田和一':{'love':[47,53,56,70,92],'like':[3,33,43,44,46,50,54,58,59,64,86,94,100,102],'dislike':[4,13,30,31,32,34,35,36,45,66,97,98,112],'hate':[22,25,28,67]},
  '花村辉辉':{'love':[29,44,67],'like':[16,17,19,20,22,25,33,48,49,66,85,86,93,101,102,108],'dislike':[4,8,9,10,11,12,13,14,15,36,40,46,110,112],'hate':[50,75,99]},
  '弐大猫丸':{'love':[19,24,42,89],'like':[8,21,33,39,51,68,78,85,86,96,102],'dislike':[4,25,36,41,54,57,58,59,62,64,66,75,97,98,100,107,112],'hate':[44,67]},
  '九头龙冬彦':{'love':[71,81],'like':[7,20,23,30,32,33,37,53,57,63,74,77,78,79,80,82,85,86,101,102,107,110],'dislike':[2,13,16,25,28,29,34,36,40,44,48,49,56,66,72,90,94,95,99,108,112],'hate':[27,67]},
  '终里赤音':{'love':[8,86],'like':[2,9,10,11,12,13,14,15,17,26,28,32,33,35,50,55,73,78,80,81,85,93,102,108,109],'dislike':[4,22,23,25,27,29,30,31,34,36,37,42,47,51,52,56,62,66,68,75,88,92,94,95,99,100,112],'hate':[40,41,45,67]},
  '七海千秋':{'love':[41,62,64,86,102],'like':[15,18,33,46,57,58,59,65,68,73,78,80,81,88],'dislike':[28,71,85,99,112],'hate':[25,34,66,93]},
  '索尼娅·内瓦曼':{'love':[11,21,74,86],'like':[2,5,6,23,29,31,32,33,35,36,38,52,54,56,63,65,70,72,75,77,78,82,85,89,92,97,98,100,102,103],'dislike':[4,9,10,14,27,28,34,66,112],'hate':[25,67]},
  '西园寺日寄子':{'love':[35,38,77,86,102],'like':[3,13,15,32,33,37,45,71,73,76,78,80,81,85,110],'dislike':[4,7,18,21,22,24,26,27,28,29,30,34,36,39,40,41,42,43,44,47,50,52,75,83,84,87,88,89,92,94,95,99,112],'hate':[25,67,97,98]},
  '小泉真昼':{'love':[32,54,82,86,102,107],'like':[22,29,33,37,39,44,71,73,78,80,81,85,93],'dislike':[4,20,21,23,24,26,27,28,34,36,42,43,45,47,48,49,52,62,64,66,76,84,88,94,99,100,112],'hate':[25,67,90,91]},
  '罪木蜜柑':{'love':[25,55,109],'like':[22,28,29,32,33,35,37,42,48,49,51,66,67,71,85,86,93,102],'dislike':[21,34,36,47,52,56,74,75,89,92,99,103,112],'hate':[88,94]},
  '澪田唯吹':{'love':[46,60,75,83,87],'like':[2,5,9,16,17,19,20,21,25,29,31,33,34,35,37,38,41,44,49,50,52,55,57,58,59,62,63,64,65,70,72,80,84,85,86,94,96,101,102,103,107,108,109,110],'dislike':[22,26,27,28,32,39,40,42,43,45,47,48,53,54,56,66,68,71,73,74,76,77,78,79,81,82,88,89,90,91,92,93,95,97,98,99,112],'hate':[4,36,67,69,100]},
  '边古山佩子':{'love':[22,71,79,86,110],'like':[7,20,24,30,32,33,37,44,57,63,74,77,78,80,81,82,85,88,101,102,107],'dislike':[2,13,16,25,27,28,29,36,48,49,56,66,72,93,108,112],'hate':[67,97,98]}
 },
 'v3': {
  '赤松枫':{'love':[45,55],'like':[2,4,9,12,19,20,25,28,30,31,32,37]},
  '夜长安吉':{'love':[4,5,9,10,12,14],'like':[2,17]},
  '狱原钢太郎':{'love':[13,20,32,41],'like':[7,9,12,14,15,23,25,27]},
  '梦野秘密子':{'love':[],'like':[3,4,7,9,13,16,19,21]},
  'Kiibo':{'love':[24,25],'like':[]},
  '百田解斗':{'love':[14,23,24],'like':[9,27]},
  '东条斩美':{'love':[3,4,6,7,8,19,20,25,32],'like':[9,12,28]},
  '王马小吉':{'love':[2,9,15,17,32],'like':[5,10,14,25]},
  '真宫寺是清':{'love':[4,9,28],'like':[21,32,36,38]},
  '春川魔姬':{'love':[2,28,30],'like':[1,4,9,11,13,18,19,23,25,31,32]},
  '入间美兔':{'love':[13,15,21],'like':[2,4,5,9,10,14,19]},
  '天海兰太郎':{'love':[2,4,5,8,9,18,19,20,25,31,32],'like':[22,30]},
  '星龙马':{'love':[16,23],'like':[3,5,9,25,30,31,32]},
  '最原终一':{'love':[32],'like':[1,2,3,9,17,19,20,23,31]},
  '茶柱转子':{'love':[2,9,23,24,26,32],'like':[3,4,10,14,31]},
  '白银紬':{'love':[9,12,19,27,28],'like':[3,4,5,17,21,23,31,32]}
 }
}

# Drop preference IDs that are not present in the supplied, title-specific catalog.
# This must run only after GIFT_PREFS has been defined (otherwise plugin import fails).
for _world, _characters in GIFT_PREFS.items():
 for _levels in _characters.values():
  for _tier, _ids in _levels.items():
   _levels[_tier] = [item_id for item_id in _ids if item_id in GIFT_CATALOG[_world]]

LOCATIONS = {
 'dr1':['学生宿舍','食堂','体育馆','图书馆','教室','校长室','洗衣房','浴室','仓库','游戏厅'],
 'dr2':['餐厅','酒店大厅','电器店','电影院','超市','药店','音乐厅','海滩小屋','遗迹','旧馆'],
 'v3':['才囚学园大厅','餐厅','教室','图书室','仓库','中庭','生物室','超高校级研究教室','礼堂','地下通道']
}

MENU = """🐻‍❄️【黑白熊电子学生手册】
━━━━━━━━━━━━━━
🎮 游戏与世界
世界观　　/弹丸 世界观 [dr1/dr2/v3]
开始游戏　/弹丸 开始
加入游戏　/弹丸 加入
游戏状态　/弹丸 状态
当前章节　/弹丸 章节
当前地图　/弹丸 地图
切换世界　/弹丸 世界观 dr1|dr2|v3

👤 学生档案
个人档案　/弹丸 个人档案
角色名册　/弹丸 角色列表
角色档案　/弹丸 角色档案 角色名
角色聊天　/弹丸 聊天 角色名 [内容]
通讯录　　/弹丸 通讯录
学生手册　/弹丸 学生手册

💗 羁绊与日常
自由行动　/弹丸 自由行动 [角色名]
赠送礼物　/弹丸 赠送 角色名 礼物名
好感度　　/弹丸 好感度 [角色名]
羁绊记录　/弹丸 羁绊
希望碎片　/弹丸 希望碎片
前往地点　/弹丸 前往 地点
探索地点　/弹丸 探索 [关键词]
日常事件　/弹丸 日常事件
角色委托　/弹丸 委托
完成委托　/弹丸 完成委托
限时活动　/弹丸 活动

🎁 道具与奖励
背包　　/弹丸 背包 [分类]
扭蛋　　/弹丸 扭蛋
十连扭蛋　/弹丸 十连
黑白熊币　/弹丸 黑白熊币
获取途径　/弹丸 黑白熊币 获取途径

🔎 非日常与裁判
杀人申请　/弹丸 杀人申请（私聊后输入目标玩家QQ号）
搜查现场　/弹丸 搜查 [地点/证据]
证据列表　/弹丸 证据
案件状态　/弹丸 案件
证词记录　/弹丸 证词
提出推理　/弹丸 推理 你的推理
学级裁判　/弹丸 学级裁判
投票　　/弹丸 投票 角色名
处刑　　/弹丸 处刑
黑白熊公告　/弹丸 公告

💾 存档管理
保存存档　/弹丸 存档
读取存档　/弹丸 读取

⚙️ 管理员（群管理员）
暂停游戏　/弹丸 管理 暂停
继续游戏　/弹丸 管理 继续
重置游戏　/弹丸 管理 重置
播报设置　/弹丸 管理 播报设置 开/关
角色互动　/弹丸 管理 角色互动 开/关
播报测试　/弹丸 管理 播报测试
触发事件　/弹丸 管理 触发事件 [日常/突发]
备份存档　/弹丸 管理 备份
恢复存档　/弹丸 管理 恢复 文件名
━━━━━━━━━━━━━━
输入 /弹丸 帮助 查看指令说明。うぷぷぷ！"""


class Store:
 def __init__(self, db_path: Path):
  db_path.parent.mkdir(parents=True, exist_ok=True)
  self.db = sqlite3.connect(db_path, check_same_thread=False)
  self.db.row_factory = sqlite3.Row
  self.db.executescript('''
  CREATE TABLE IF NOT EXISTS room_settings(base_room TEXT PRIMARY KEY, active_world TEXT NOT NULL DEFAULT 'dr1');
  CREATE TABLE IF NOT EXISTS rooms(room TEXT PRIMARY KEY, world TEXT NOT NULL DEFAULT 'dr1', started INTEGER DEFAULT 0, paused INTEGER DEFAULT 0, chapter INTEGER DEFAULT 1, day INTEGER DEFAULT 1, phase TEXT DEFAULT '日常生活', broadcast INTEGER DEFAULT 1, character_broadcast INTEGER DEFAULT 1, coins INTEGER DEFAULT 100, location TEXT DEFAULT '', case_json TEXT DEFAULT '', saved_json TEXT DEFAULT '');
  CREATE TABLE IF NOT EXISTS players(room TEXT, uid TEXT, name TEXT, talent TEXT DEFAULT '', location TEXT DEFAULT '', alive INTEGER DEFAULT 1, joined INTEGER DEFAULT 0, PRIMARY KEY(room,uid));
  CREATE TABLE IF NOT EXISTS bonds(room TEXT, uid TEXT, character TEXT, value INTEGER DEFAULT 0, PRIMARY KEY(room,uid,character));
  CREATE TABLE IF NOT EXISTS inventory(room TEXT, uid TEXT, item TEXT, category TEXT, amount INTEGER DEFAULT 1, PRIMARY KEY(room,uid,item,category));
  CREATE TABLE IF NOT EXISTS evidence(room TEXT, evidence TEXT, detail TEXT, PRIMARY KEY(room,evidence));
  CREATE TABLE IF NOT EXISTS votes(room TEXT, uid TEXT, target TEXT, PRIMARY KEY(room,uid));
  CREATE TABLE IF NOT EXISTS private_actions(room TEXT, uid TEXT, action TEXT, payload TEXT, created INTEGER);
  CREATE TABLE IF NOT EXISTS chat_memory(room TEXT, uid TEXT, character TEXT, role TEXT, content TEXT, created INTEGER);
  CREATE TABLE IF NOT EXISTS room_targets(room TEXT PRIMARY KEY, umo TEXT NOT NULL, last_broadcast_at INTEGER NOT NULL DEFAULT 0, daily_date TEXT NOT NULL DEFAULT '', daily_count INTEGER NOT NULL DEFAULT 0);
  CREATE TABLE IF NOT EXISTS coin_reward_claims(room TEXT NOT NULL, uid TEXT NOT NULL, claim_key TEXT NOT NULL, claim_date TEXT NOT NULL, amount INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(room,uid,claim_key,claim_date));
  CREATE TABLE IF NOT EXISTS coin_reward_events(room TEXT NOT NULL, event_key TEXT NOT NULL, amount INTEGER NOT NULL DEFAULT 0, created INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(room,event_key));
   CREATE TABLE IF NOT EXISTS pending_kill_requests(uid TEXT PRIMARY KEY, room TEXT NOT NULL, created INTEGER NOT NULL);
   CREATE TABLE IF NOT EXISTS coin_commissions(room TEXT NOT NULL, uid TEXT NOT NULL, day TEXT NOT NULL, task TEXT NOT NULL, done INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(room,uid,day));
  CREATE TABLE IF NOT EXISTS character_memories(world TEXT NOT NULL, uid TEXT NOT NULL, character TEXT NOT NULL, first_seen INTEGER NOT NULL DEFAULT 0, last_seen INTEGER NOT NULL DEFAULT 0, interaction_count INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(world,uid,character));
  CREATE TABLE IF NOT EXISTS character_memory_logs(world TEXT NOT NULL, uid TEXT NOT NULL, character TEXT NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, created INTEGER NOT NULL, room TEXT NOT NULL DEFAULT '', is_private INTEGER NOT NULL DEFAULT 0);
  CREATE TABLE IF NOT EXISTS bond_scenes(room TEXT NOT NULL, uid TEXT NOT NULL, character TEXT NOT NULL, stage INTEGER NOT NULL, unlocked_at INTEGER NOT NULL, PRIMARY KEY(room,uid,character,stage));
  CREATE TABLE IF NOT EXISTS bond_rewards(room TEXT NOT NULL, uid TEXT NOT NULL, character TEXT NOT NULL, granted_at INTEGER NOT NULL, PRIMARY KEY(room,uid,character));
  ''')
  # Schema upgrades for databases created by earlier plugin versions.
  room_cols={z['name'] for z in self.db.execute('PRAGMA table_info(rooms)')}
  if 'character_broadcast' not in room_cols:
   self.db.execute('ALTER TABLE rooms ADD COLUMN character_broadcast INTEGER NOT NULL DEFAULT 1')
  self.db.execute('UPDATE rooms SET broadcast=1 WHERE broadcast IS NULL')
  self.db.execute('UPDATE rooms SET character_broadcast=1 WHERE character_broadcast IS NULL')
  self.db.execute('CREATE INDEX IF NOT EXISTS idx_character_memory_lookup ON character_memory_logs(world,uid,character,created)')
  # Remove legacy plugin-invented gifts so they cannot remain in the active bag/gacha loop.
  self.db.execute('DELETE FROM inventory WHERE category="礼物" AND item IN ("普通礼物盒","闪亮纪念徽章","可爱玩偶","星形糖果","神秘包装礼物")')
  # Migration: players who already reached 100 before this feature receive the
  # corresponding character keepsake once; the unique claim key prevents duplicates.
  maxed=self.db.execute('SELECT room,uid,character FROM bonds WHERE value>=100').fetchall()
  for row in maxed:
   cur=self.db.execute('INSERT OR IGNORE INTO bond_rewards(room,uid,character,granted_at) VALUES(?,?,?,?)',(row['room'],row['uid'],row['character'],int(time.time())))
   if cur.rowcount:
    self.db.execute('INSERT INTO inventory(room,uid,item,category,amount) VALUES(?,?,?,"羁绊纪念品",1) ON CONFLICT(room,uid,item,category) DO UPDATE SET amount=amount+1',(row['room'],row['uid'],f'{row["character"]}的内裤'))
  self.db.commit()
 def room(self, room):
  world=room.rsplit('::',1)[-1] if '::' in room else 'dr1'
  self.db.execute('INSERT OR IGNORE INTO rooms(room,world) VALUES(?,?)',(room,world)); self.db.commit()
  return self.db.execute('SELECT * FROM rooms WHERE room=?',(room,)).fetchone()
 def active_world(self, base_room):
  self.db.execute("INSERT OR IGNORE INTO room_settings(base_room,active_world) VALUES(?,'dr1')",(base_room,))
  row=self.db.execute('SELECT active_world FROM room_settings WHERE base_room=?',(base_room,)).fetchone()
  return row['active_world']
 def player(self, room, uid): return self.db.execute('SELECT * FROM players WHERE room=? AND uid=?',(room,uid)).fetchone()
 def save(self): self.db.commit()

class DanganronpaPlugin(Star):
 def __init__(self, context: Context, config: AstrBotConfig):
  super().__init__(context)
  self.config=config
  PLUGIN_DATA.mkdir(parents=True, exist_ok=True)
  BACKUP_DIR.mkdir(parents=True, exist_ok=True)
  # 兼容旧版：首次启动时将插件目录中的 SQLite 迁移到 AstrBot plugin_data。
  if not DB.exists() and LEGACY_DB.is_file():
   shutil.copy2(LEGACY_DB, DB)
   logger.warning('弹丸论破：已迁移旧版数据库到 AstrBot plugin_data。')
  self.store=Store(DB)
  self.rng=random.Random()
  self._broadcast_task=None
  try: self.mono_expressions=json.loads((ROOT/'personas/monokuma/expressions.json').read_text(encoding='utf-8')).get('laughs',[])
  except Exception: self.mono_expressions=[]
  logger.info('弹丸论破互动模拟器已加载；持久化数据库：%s', DB)

 async def initialize(self):
  # AstrBot 插件生命周期钩子：在事件循环可用后启动后台调度器。
  if self._broadcast_task is None or self._broadcast_task.done():
   self._broadcast_task=asyncio.create_task(self._broadcast_loop())

 def _room_uid(self,event):
  try: room=event.get_group_id() or f'private:{event.get_sender_id()}'
  except Exception: room=f'private:{event.get_sender_id()}'
  return str(room),str(event.get_sender_id())
 def _private(self,event):
  try: return not bool(event.get_group_id())
  except Exception: return True
 def _name(self,event):
  try: return event.get_sender_name() or str(event.get_sender_id())
  except Exception: return str(event.get_sender_id())
 def _mono(self,msg):
  laugh=(self.rng.choice(self.mono_expressions)+' ') if self.mono_expressions and self.rng.random()<0.22 else ''
  return f'🐻‍❄️ 黑白熊：{laugh}{msg}'
 def _need_game(self,room):
  r=self.store.room(room)
  return r if r['started'] else None
 def _player(self,room,uid,name):
  p=self.store.player(room,uid)
  if not p:
   return None
  return p
 @staticmethod
 def _pretty_lines(lines):
  """构造单条 QQ 消息中的真实多行文本，保护首尾换行不被 Plain 序列化剥除。"""
  normalized=[]
  for line in lines:
   normalized.append(str(line).replace("\r\n","\n").replace("\r","\n").strip())
  while normalized and not normalized[-1]: normalized.pop()
  return "\u200b" + "\n".join(normalized) + "\u200b"

 @staticmethod
 def _format_command_output(text):
  """统一整理所有指令/播报的版式，结构字段逐行显示，黑白熊署名单独占行。"""
  value=str(text or "").replace("\r\n","\n").replace("\r","\n").replace("\\n","\n").strip()
  if not value:
   return "\u200b\u200b"

  # 角色对话有专用格式化器；这里处理普通功能输出和黑白熊公告。
  prefix="🐻‍❄️ 黑白熊："
  has_mono=value.startswith(prefix)
  if has_mono:
   value=value[len(prefix):].lstrip()

  # 把紧凑的键值串拆成独立字段。仅在逗号后紧跟明确字段名时拆分，
  # 不会把普通叙述句中的逗号全部切碎。
  labels=(
   "世界","状态","地点","学生人数","生存名单","姓名","才能","所在地点",
   "黑白熊币","章节","日期","阶段","存活学生","证据数","被害者",
   "案发地点","当前阶段","已发现证据","好感度","剩余黑白熊币",
   "今日已获得奖励","搜查奖励","探索奖励","章节通关奖励","当前投票数",
   "投票对象","玩家","角色","所属作品","当前世界","当前地点",
   "当前章节","当前日期","当前阶段","凶手","目标","案发时间",
   "奖励","背包物品","互动次数","关系阶段"
  )
  label_pattern="|".join(re.escape(x) for x in sorted(set(labels),key=len,reverse=True))
  value=re.sub(r"[，,](?=(?:"+label_pattern+r")[：:])","\n",value)
  # 章节/天数/阶段这一类无冒号的进度段，也独立成行并补上字段名。
  value=re.sub(r"[，,](?=第\d+章\s*/\s*第\d+天)","\n进度：",value)

  lines=[]
  for raw_line in value.split("\n"):
   line=raw_line.strip()
   if not line:
    if lines and lines[-1] != "": lines.append("")
    continue
   # 若进度段原本位于独立行，也补充明确的字段名。
   if re.match(r"^第\d+章\s*/\s*第\d+天",line):
    line="进度："+line
   lines.append(line)
  while lines and not lines[-1]: lines.pop()
  if has_mono:
   lines.insert(0,prefix.rstrip())
  return "\n".join(lines)

 @staticmethod
 def _format_role_dialogue(character,text):
  """把模型输出强制整理为角色名、动作、逐句台词的多行格式。"""
  value=str(text or "").replace("\r\n","\n").replace("\r","\n").replace("\\n","\n").strip()
  value=re.sub(r"^```(?:text|markdown)?\s*|\s*```$","",value,flags=re.I)
  header=re.search(r"\*\*?【[^】]+】\*\*?\s*",value)
  if header:
   value=value[header.end():]
  else:
   value=re.sub(r"^\s*【[^】]+】\s*","",value)
  value=value.lstrip(" \t，,、；;：:")
  value=re.sub(rf"^\s*{re.escape(character)}\s*[，,：:、。；;\-—]*\s*","",value)
  value=value.strip(" \t，,、；;：:")
  action=""
  action_matches=list(re.finditer(r"[（(]([^（）()]{1,100})[）)]",value))
  if action_matches:
   first=action_matches[0]
   action_text=first.group(1).strip()
   if not re.search(r"[。！？!?…]$",action_text):
    action_text+="。"
   action="（"+action_text+"）"
   value=value[:first.start()]+" "+value[first.end():]
   value=re.sub(r"[（(][^（）()]{1,100}[）)]"," ",value)
  quoted=re.findall(r"「([^」]+)」|『([^』]+)』|“([^”]+)”",value)
  if quoted:
   # Respect the model's existing quoted paragraph breaks.
   parts=[next((part for part in group if part), "").strip() for group in quoted]
  else:
   dialogue=value.replace("**","").strip()
   dialogue=re.sub(r"^[\s，,、；;：:。！？!?]+","",dialogue)
   parts=[]
   for line in dialogue.splitlines():
    parts.extend(re.split(r"(?<=[。！？!?])\s*",line.strip()))
  parts=[p.strip(" \t，,、；;：:「」『』“”") for p in parts if p.strip(" \t，,、；;：:「」『』“”")]
  parts=parts[:3]
  lines=[f"**【{character}】**"]
  if action:
   lines.append(action)
  for part in parts:
   if not re.search(r"[。！？!?…]$",part):
    part+="。"
   lines.append(f"「{part}」")
  if len(lines)==1:
   lines.append("「……我听到了。」")
  return "\n".join(lines)

 @staticmethod
 async def _send_formatted(event,text):
  """绕过普通回复装饰管道，直接发送保留换行的单条消息。"""
  chain=MessageChain().message(str(text))
  await event.send(chain)

 def _reply(self,event,msg): return event.plain_result(msg)
 def _is_admin(self,event):
  # AstrBot event API differs slightly between adapters; support standard admin flags and explicit configured IDs.
  try:
   if event.is_admin(): return True
  except Exception: pass
  try:
   ids=self.config.get('admins',[]) if hasattr(self.config,'get') else []
   return str(event.get_sender_id()) in {str(x) for x in ids}
  except Exception: return False

 @filter.command('弹丸')
 async def command(self,event:AstrMessageEvent):
  '''弹丸论破互动模拟器总入口：/弹丸 菜单 或 /弹丸 帮助'''
  try:
   raw=(event.message_str or '').strip()
   args=raw.split()
   # command text may include the command itself depending on AstrBot adapter
   if args and args[0].startswith('/'): args=args[1:]
   if args and args[0]=='弹丸': args=args[1:]
   base_room,uid=self._room_uid(event); name=self._name(event)
   world=self.store.active_world(base_room); room=f'{base_room}::{world}'; r=self.store.room(room)
   if not self._private(event):
    umo=getattr(event,'unified_msg_origin',None)
    if umo:
     self.store.db.execute('INSERT INTO room_targets(room,umo,last_broadcast_at) VALUES(?,?,?) ON CONFLICT(room) DO UPDATE SET umo=excluded.umo',(room,str(umo),int(time.time())))
   if not args or args[0] in ('菜单','帮助','menu','help'):
    self.store.save()
    # 优先发送插件内置的电子学生手册图片；图片文件缺失时回退到同一多行发送链路。
    if MENU_IMAGE.is_file():
     yield event.image_result(str(MENU_IMAGE))
    else:
     menu_text=self._format_command_output(MENU)
     await self._send_formatted(event,self._pretty_lines(menu_text.splitlines()))
    return
   action=args[0]; rest=args[1:]
   result=await self._dispatch(event,room,uid,name,r,action,rest)
   self.store.save()
   formatted=self._format_command_output(result)
   await self._send_formatted(event,self._pretty_lines(formatted.splitlines()))
  except Exception as e:
   logger.error('弹丸插件命令异常：%s\n%s',e,traceback.format_exc())
   error_text=self._format_command_output(self._mono('呜噗！这一步执行时出了点故障。\n请检查参数后重试；错误已写入 AstrBot 日志。'))
   await self._send_formatted(event,self._pretty_lines(error_text.splitlines()))

 @filter.event_message_type(filter.EventMessageType.PRIVATE_MESSAGE, priority=100)
 async def on_private_kill_target(self,event:AstrMessageEvent):
  """只处理处于杀人申请待填写状态的私聊纯数字 QQ 号。"""
  uid=str(event.get_sender_id())
  text=(event.message_str or '').strip()
  if not re.fullmatch(r'\d{5,12}',text):
   return
  pending=self.store.db.execute('SELECT room,created FROM pending_kill_requests WHERE uid=?',(uid,)).fetchone()
  if not pending:
   return
  event.stop_event()
  if int(time.time())-int(pending['created'])>600:
   self.store.db.execute('DELETE FROM pending_kill_requests WHERE uid=?',(uid,))
   self.store.save()
   await self._send_formatted(event,self._pretty_lines(self._format_command_output(self._mono('这次杀人申请已超时，请重新发送 /弹丸 杀人申请。')).splitlines()))
   return
  room=str(pending['room']); db=self.store.db; applicant=db.execute('SELECT * FROM players WHERE room=? AND uid=?',(room,uid)).fetchone()
  game=self.store.room(room)
  if not applicant or not applicant['alive'] or not game['started'] or game['paused'] or game['case_json']:
   db.execute('DELETE FROM pending_kill_requests WHERE uid=?',(uid,)); self.store.save()
   await self._send_formatted(event,self._pretty_lines(self._format_command_output(self._mono('当前玩家或游戏状态已不符合申请条件，待处理申请已取消。')).splitlines()))
   return
  target_uid=text
  if target_uid==uid:
   await self._send_formatted(event,self._pretty_lines(self._format_command_output(self._mono('不能选择自己作为目标。请重新发送另一位已加入当前游戏的玩家 QQ 号。')).splitlines()))
   return
  victim=db.execute('SELECT * FROM players WHERE room=? AND uid=?',(room,target_uid)).fetchone()
  if not victim:
   await self._send_formatted(event,self._pretty_lines(self._format_command_output(self._mono('这个 QQ 号对应的玩家没有加入你当前群聊的游戏世界。请核对 QQ 号后重试。')).splitlines()))
   return
  if not victim['alive']:
   await self._send_formatted(event,self._pretty_lines(self._format_command_output(self._mono('目标玩家已经被淘汰，不能再次成为杀人目标。请重新输入其他玩家 QQ 号。')).splitlines()))
   return
  scene_pool=[place for place in LOCATIONS[game['world']] if place!=game['location']]
  scene=self.rng.choice(scene_pool or LOCATIONS[game['world']])
  case=await self._plan_case(event,game['world'],applicant['name'],victim['name'],scene)
  case.update({'victim':victim['name'],'culprit':applicant['name'],'applicant':applicant['name'],'applicant_uid':uid,'victim_uid':target_uid,'scene':scene,'created':int(time.time()),'revealed':0})
  db.execute('UPDATE rooms SET case_json=?,phase="尸体发现" WHERE room=?',(json.dumps(case,ensure_ascii=False),room))
  db.execute('INSERT INTO private_actions(room,uid,action,payload,created) VALUES(?,?,?,?,?)',(room,uid,'杀人申请',json.dumps({'target_uid':target_uid,'target':victim['name'],'scene':scene},ensure_ascii=False),int(time.time())))
  db.execute('DELETE FROM pending_kill_requests WHERE uid=?',(uid,))
  self.store.save()
  response=self._mono(f'うぷぷぷ！秘密申请已确认。目标玩家：{victim["name"]}（QQ：{target_uid}）。案发地点：{scene}。申请与目标信息仅向你私聊反馈；群聊公告不会泄露申请者身份。请等待尸体发现公告。')
  event.stop_event()
  await self._send_formatted(event,self._pretty_lines(self._format_command_output(response).splitlines()))

 async def _dispatch(self,event,room,uid,name,r,a,x):
  s=self.store; db=s.db
  if a=='世界观':
   if not x: return self._mono('当前世界：'+WORLD_NAMES[r['world']]+'。可选：dr1、dr2、v3。')
   w=x[0].lower()
   if w not in WORLD_NAMES: return self._mono('世界观参数无效，请使用 dr1、dr2 或 v3。')
   base=room.rsplit('::',1)[0]
   db.execute('INSERT INTO room_settings(base_room,active_world) VALUES(?,?) ON CONFLICT(base_room) DO UPDATE SET active_world=excluded.active_world',(base,w))
   new_room=f'{base}::{w}'
   s.room(new_room)
   if not self._private(event):
    umo=getattr(event,'unified_msg_origin',None)
    if umo:
     db.execute('INSERT INTO room_targets(room,umo,last_broadcast_at) VALUES(?,?,?) ON CONFLICT(room) DO UPDATE SET umo=excluded.umo',(new_room,str(umo),int(time.time())))
   return self._mono('当前世界已切换为「'+WORLD_NAMES[w]+'」。每个世界都有独立的玩家进度、物品、案件和存档，原世界数据不会覆盖。')
  if a=='开始':
   if r['started']: return self._mono('本房间已经有进行中的游戏。输入 /弹丸 状态 查看进度。')
   db.execute('UPDATE rooms SET started=1,paused=0,chapter=1,day=1,phase="日常生活",location=?,case_json="" WHERE room=?',(LOCATIONS[r['world']][0],room))
   db.execute('INSERT OR IGNORE INTO players(room,uid,name,location,joined) VALUES(?,?,?,?,1)',(room,uid,name,LOCATIONS[r['world']][0]))
   p=s.player(room,uid)
   # 才能只在首次建档时随机抽取；已有才能绝不因重新开始或升级而重抽。
   if not p['talent']:
    talent=self._talent(name,uid)
    db.execute('UPDATE players SET talent=? WHERE room=? AND uid=?',(talent,room,uid))
   else:
    talent=p['talent']
   return self._mono(f'欢迎来到{WORLD_NAMES[r["world"]]}！哇哈哈哈哈！\n追加学生：{name}\n超高校级的才能：{talent}\n你已成为本房间的额外学生。输入 /弹丸 菜单 查看电子学生手册。')
  if a=='加入':
   if not r['started']: return self._mono('本房间还没有开始游戏。请先输入 /弹丸 开始。')
   db.execute('INSERT OR IGNORE INTO players(room,uid,name,location,joined) VALUES(?,?,?,?,1)',(room,uid,name,r['location']))
   p=s.player(room,uid)
   if not p['talent']: db.execute('UPDATE players SET talent=? WHERE room=? AND uid=?',(self._talent(name,uid),room,uid))
   return self._mono(f'{name} 已加入班级！超高校级的才能：{db.execute("SELECT talent FROM players WHERE room=? AND uid=?",(room,uid)).fetchone()[0]}。')
  if a=='状态':
   players=db.execute('SELECT name,alive,talent FROM players WHERE room=?',(room,)).fetchall()
   return self._mono(f'世界：{WORLD_NAMES[r["world"]]}\n状态：{"未开始" if not r["started"] else "已暂停" if r["paused"] else "进行中"}\n第{r["chapter"]}章 / 第{r["day"]}天 / {r["phase"]}\n地点：{r["location"] or "未设置"}\n学生人数：{len(players)}\n生存名单：'+('、'.join(p['name'] for p in players if p['alive']) or '暂无'))
  if a=='管理': return await self._admin(event,room,r,x)
  if r['paused'] and a not in ('状态','帮助','公告'): return self._mono('当前游戏已暂停，玩家行动暂时冻结。请等待管理员 /弹丸 管理 继续。')
  if a=='存档':
   snap=self._snapshot(room); db.execute('UPDATE rooms SET saved_json=? WHERE room=?',(json.dumps(snap,ensure_ascii=False),room)); return self._mono('当前世界存档已保存。其他世界存档相互独立。')
  if a=='读取':
   data=r['saved_json']
   if not data: return self._mono('当前世界还没有手动存档。')
   self._restore(room,json.loads(data)); return self._mono('已读取当前世界最近一次手动存档。')
  if a=='个人档案':
   p=s.player(room,uid)
   if not p: return self._mono('你还没有加入本房间。输入 /弹丸 加入。')
   return self._mono(f'姓名：{p["name"]}\n才能：{p["talent"] or "未判定"}\n所在地点：{p["location"]}\n状态：{"存活" if p["alive"] else "已淘汰"}\n黑白熊币：{r["coins"]}')
  if a=='角色列表': return self._mono(f'{WORLD_NAMES[r["world"]]}角色名册：\n'+'、'.join(ROSTERS[r['world']]))
  if a=='角色档案':
   if not x: return self._mono('用法：/弹丸 角色档案 角色名')
   ch=' '.join(x); return self._character_card(r['world'],ch)
  if a=='聊天':
   if not x: return self._mono('用法：/弹丸 聊天 角色名 [内容]')
   ch=x[0]; msg=' '.join(x[1:]) or '你好。'
   if ch not in ROSTERS[r['world']]: return self._mono('当前世界名册中没有这名角色，请检查作品和名字。')
   return await self._chat(event,room,uid,ch,msg)
  if a=='通讯录': return self._mono('【通讯录】\n'+'\n'.join(f'• {n}　好感 {self._bond(room,uid,n)}' for n in ROSTERS[r['world']]))
  if a=='学生手册': return self._mono(f'【电子学生手册】\n世界：{WORLD_NAMES[r["world"]]}\n章节：第{r["chapter"]}章\n日期：第{r["day"]}天\n阶段：{r["phase"]}\n地点：{r["location"]}\n存活学生：{db.execute("SELECT COUNT(*) FROM players WHERE room=? AND alive=1",(room,)).fetchone()[0]}\n证据数：{db.execute("SELECT COUNT(*) FROM evidence WHERE room=?",(room,)).fetchone()[0]}')
  if a in ('自由行动','赠送','好感度'):
   p=s.player(room,uid)
   if not p: return self._mono('请先 /弹丸 加入。')
   if a=='自由行动':
    if not x: return self._mono('请选择一位角色：/弹丸 自由行动 角色名。先用 /弹丸 角色列表 查看名册。')
    ch=' '.join(x)
    if ch not in ROSTERS[r['world']]: return self._mono('当前世界名册中没有这名角色，请检查作品和名字。')
    db.execute('INSERT OR IGNORE INTO bonds(room,uid,character,value) VALUES(?,?,?,0)',(room,uid,ch))
    before=self._bond(room,uid,ch)
    db.execute('UPDATE bonds SET value=MIN(100,value+5) WHERE room=? AND uid=? AND character=?',(room,uid,ch))
    after=self._bond(room,uid,ch)
    underwear=self._grant_bond_underwear(room,uid,ch,after)
    milestone=self._claim_bond_scene(room,uid,ch,before,after)
    if milestone:
     scene=f'羁绊阶段突破：{self._bond_stage(after)}。请演绎一段有起承转合、符合{ch}原作性格的专属关系剧情，地点为{r["location"] or LOCATIONS[r["world"]][0]}。这是阶段剧情，不是普通寒暄；不要擅自改变原作重大设定，不要直接告白或突然亲密。'
    else:
     scene=f'在{r["location"] or LOCATIONS[r["world"]][0]}与玩家进行一段自由时间互动。'
    reply=await self._chat(event,room,uid,ch,scene)
    earned,remaining=self._award_coins(room,uid,f'free:{ch}',(20,50))
    reward_text=f'\n黑白熊币 +{earned}' if earned else '\n这位角色的自由行动奖励今日已领取。'
    commission_done=self._progress_commission(room,uid,'free')
    if commission_done: reward_text+='\n角色委托已完成，输入 /弹丸 完成委托 领取奖励。'
    bond_reward=0
    if milestone:
     bond_reward,_=self._award_coins(room,uid,f'bond:{ch}:{milestone}',(20,40))
     if bond_reward: reward_text+=f'\n首次解锁羁绊阶段奖励：黑白熊币 +{bond_reward}'
    underwear_text='\n羁绊奖励：获得「'+ch+'的内裤」！已放入背包。' if underwear else ''
    return self._mono(f'【自由时间】好感度 +5（当前 {self._bond(room,uid,ch)}/100）{underwear_text}{reward_text}\n{reply}')
   if a=='赠送':
    if len(x)<2: return self._mono('用法：/弹丸 赠送 角色名 礼物名')
    ch=x[0]; item=' '.join(x[1:])
    if ch not in ROSTERS[r['world']]: return self._mono('当前世界名册中没有这名角色，请检查作品和名字。')
    item_id=GIFT_NAME_TO_ID[r['world']].get(item)
    if item_id is None: return self._mono(f'「{item}」不是当前作品礼物目录中的物品。请先查看 /弹丸 背包。')
    have=db.execute('SELECT amount FROM inventory WHERE room=? AND uid=? AND item=? AND category="礼物"',(room,uid,item)).fetchone()
    if not have: return self._mono(f'背包里没有「{item}」。')
    db.execute('UPDATE inventory SET amount=amount-1 WHERE room=? AND uid=? AND item=? AND category="礼物"',(room,uid,item))
    db.execute('DELETE FROM inventory WHERE room=? AND uid=? AND item=? AND category="礼物" AND amount<=0',(room,uid,item))
    pref=GIFT_PREFS.get(r['world'],{}).get(ch,{})
    tier=next((k for k in ('love','like','dislike','hate') if item_id in pref.get(k,[])),'medium')
    before=self._bond(room,uid,ch)
    delta={'love':5,'like':3,'medium':0,'dislike':0,'hate':0}[tier]
    if delta:
     db.execute('INSERT OR IGNORE INTO bonds(room,uid,character,value) VALUES(?,?,?,0)',(room,uid,ch))
     db.execute('UPDATE bonds SET value=MIN(100,value+?) WHERE room=? AND uid=? AND character=?',(delta,room,uid,ch))
    after=self._bond(room,uid,ch)
    underwear=self._grant_bond_underwear(room,uid,ch,after) if delta else False
    milestone=self._claim_bond_scene(room,uid,ch,before,after) if delta else None
    bond_reward=0
    if milestone:
     bond_reward,_=self._award_coins(room,uid,f'bond:{ch}:{milestone}',(20,40))
    reaction={'love':'很喜欢','like':'喜欢','medium':'中等','dislike':'不喜欢','hate':'厌恶'}[tier]
    lines=[f'你把「{item}」送给了{ch}。',f'角色反应：{reaction}。']
    if delta: lines.append(f'好感度 +{delta}（当前 {after}/100）。')
    else: lines.append(f'好感度没有变化（当前 {after}/100）。')
    if underwear: lines.append(f'羁绊奖励：获得「{ch}的内裤」！已放入背包。')
    if milestone:
     lines.append(f'羁绊阶段提升：{self._bond_stage(after)}。')
     if bond_reward: lines.append(f'首次解锁羁绊阶段奖励：黑白熊币 +{bond_reward}。')
     story_scene=f'羁绊阶段突破：{self._bond_stage(after)}。请演绎一段有起承转合、符合{ch}原作性格的专属关系剧情，地点为{r["location"] or LOCATIONS[r["world"]][0]}。这是阶段剧情，不是普通寒暄；不要擅自改变原作重大设定，不要直接告白或突然亲密。'
     story_reply=await self._chat(event,room,uid,ch,story_scene)
     lines.append(story_reply)
    return self._mono('\n'.join(lines))
   if not x: return self._mono('用法：/弹丸 好感度 [角色名]')
   ch=' '.join(x); return self._mono(f'{ch} 对你的好感度：{self._bond(room,uid,ch)} / 100')
  if a=='前往':
   if not x: return self._mono('用法：/弹丸 前往 地点')
   loc=' '.join(x)
   if loc not in LOCATIONS[r['world']]: return self._mono('这个地点不在当前世界地图中。可用地点：'+'、'.join(LOCATIONS[r['world']]))
   db.execute('UPDATE rooms SET location=? WHERE room=?',(loc,room)); db.execute('UPDATE players SET location=? WHERE room=? AND uid=?',(loc,room,uid))
   return self._mono(f'你前往了「{loc}」。')
  if a=='探索':
   if not r['started']: return self._mono('请先开始游戏。')
   loc=r['location']; case=json.loads(r['case_json'] or '{}')
   if r['phase']=='搜查' and case:
    ev=case.get('evidence',[]); idx=int(case.get('revealed',0))
    if idx>=len(ev): return self._mono('这宗案件的现场线索已经全部收集完毕。请查看 /弹丸 证据，整理矛盾后进入学级裁判。')
    clue=ev[idx]
    db.execute('INSERT OR IGNORE INTO evidence(room,evidence,detail) VALUES(?,?,?)',(room,clue['name'],clue['detail']))
    case['revealed']=idx+1
    db.execute('UPDATE rooms SET case_json=? WHERE room=?',(json.dumps(case,ensure_ascii=False),room))
    earned,remaining=self._award_coins(room,uid,f'evidence:{clue["name"]}',(10,30))
    reward_text=f'\n搜查奖励：黑白熊币 +{earned}' if earned else '\n这条证据的奖励今日已领取。'
    return self._mono(f'【新证据】{clue["name"]}：{clue["detail"]}\n已收集 {idx+1}/{len(ev)} 项。{reward_text}\n继续 /弹丸 探索 可寻找下一条线索。')
   earned,remaining=self._award_coins(room,uid,f'explore:{loc}',(10,40))
   reward_text=f'\n探索奖励：黑白熊币 +{earned}' if earned else '\n这个地点的探索奖励今日已领取。'
   return self._mono(f'你仔细探索了{loc}，发现一些日常线索。当前阶段为{r["phase"]}。{reward_text}')
  if a in ('扭蛋','十连'):
   if not s.player(room,uid): return self._mono('请先加入游戏。')
   count=10 if a=='十连' else 1; cost=10*count
   if r['coins']<cost: return self._mono(f'黑白熊币不足！需要{cost}枚，你目前有{r["coins"]}枚。')
   db.execute('UPDATE rooms SET coins=coins-? WHERE room=?',(cost,room)); items=[]
   pool=list(GIFT_CATALOG[r['world']].values())
   for _ in range(count):
    item=self.rng.choice(pool); items.append(item); db.execute('INSERT INTO inventory(room,uid,item,category,amount) VALUES(?,?,?,"礼物",1) ON CONFLICT(room,uid,item,category) DO UPDATE SET amount=amount+1',(room,uid,item))
   return self._mono(f'扭蛋结果：\n'+'\n'.join(f'· {i}' for i in items)+f'\n剩余黑白熊币：{r["coins"]-cost}')
  if a=='背包':
   if x:
    rows=db.execute('SELECT item,category,amount FROM inventory WHERE room=? AND uid=? AND category=? AND amount>0',(room,uid,x[0])).fetchall()
   else:
    rows=db.execute('SELECT item,category,amount FROM inventory WHERE room=? AND uid=? AND amount>0',(room,uid)).fetchall()
   return self._mono('【背包】\n'+('\n'.join(f'{z["category"]}｜{z["item"]} ×{z["amount"]}' for z in rows) if rows else '该分类下没有物品。'))
  if a=='委托':
   if not s.player(room,uid): return self._mono('请先加入游戏。')
   today=self._now().strftime('%Y-%m-%d')
   row=db.execute('SELECT task,done FROM coin_commissions WHERE room=? AND uid=? AND day=?',(room,uid,today)).fetchone()
   if not row:
    task=self.rng.choice(['自由行动一次','探索地点一次','触发日常事件一次'])
    db.execute('INSERT INTO coin_commissions(room,uid,day,task,done) VALUES(?,?,?,?,0)',(room,uid,today,task))
    return self._mono(f'今日角色委托：{task}。完成后输入 /弹丸 完成委托 领取 30～60 枚随机黑白熊币。')
   return self._mono(f'今日角色委托：{row["task"]}。状态：{"已完成" if row["done"] else "进行中"}。')
  if a=='完成委托':
   today=self._now().strftime('%Y-%m-%d')
   row=db.execute('SELECT task,done FROM coin_commissions WHERE room=? AND uid=? AND day=?',(room,uid,today)).fetchone()
   if not row: return self._mono('你今天还没有领取角色委托。先输入 /弹丸 委托。')
   if not row['done']: return self._mono(f'委托尚未完成：{row["task"]}。完成对应行动后再来领取。')
   earned,_=self._award_coins(room,uid,'commission:'+today,(30,60))
   return self._mono(f'委托奖励：黑白熊币 +{earned}。' if earned else '今天的委托奖励已经领取。')
  if a=='活动':
   if not s.player(room,uid): return self._mono('请先加入游戏。')
   earned,_=self._award_coins(room,uid,'special_event',(30,80))
   return self._mono(f'参与今日特别活动，获得黑白熊币 +{earned}！' if earned else '今日特别活动奖励已经领取，请留意后续活动。')
  if a=='黑白熊币':
   if x and x[0] in ('获取途径','途径','说明'):
    return self._mono(
     '【黑白熊币获取途径】\n'
     '自由行动：20～50 枚随机奖励（同一角色每日一次）。\n'
     '探索地点：10～40 枚随机奖励（同一地点每日一次）。\n'
     '发现新证据：10～30 枚随机奖励（每条证据每日一次）。\n'
     '日常随机事件：20～50 枚随机奖励（每日一次）。\n'
     '完成章节：全班共享 50～100 枚随机奖励。\n'
     '学级裁判：命中案件关键推理、正确投票可获得额外奖励。\n'
     '羁绊阶段：首次解锁新阶段时获得奖励。\n'
     '角色委托：完成当日委托获得 30～60 枚。\n'
     '特殊活动：参与活动领取随机奖励。\n'
     '所有奖励均无每日累计上限；单项事件仍按事件次数去重。'
    )
   today=self._now().strftime('%Y-%m-%d')
   earned=db.execute('SELECT COALESCE(SUM(amount),0) FROM coin_reward_claims WHERE room=? AND uid=? AND claim_date=?',(room,uid,today)).fetchone()[0]
   return self._mono(f'本房间共享黑白熊币：{r["coins"]}。\\n你今日已获得奖励：{earned} 枚。\\n输入 /弹丸 黑白熊币 获取途径 查看全部获取方式。每日累计奖励没有上限。')
  if a=='杀人申请':
   if not self._private(event):
    return self._mono('杀人申请属于秘密行动！请私聊机器人发送 /弹丸 杀人申请。')
   if x:
    return self._mono('现在请先发送 /弹丸 杀人申请，随后按提示单独发送目标玩家的 QQ 号。')
   active=db.execute("SELECT p.room,p.name,p.alive FROM players p JOIN room_settings rs ON p.room=rs.base_room || '::' || rs.active_world WHERE p.uid=? AND p.room NOT LIKE 'private:%' ORDER BY p.rowid DESC LIMIT 1",(uid,)).fetchone()
   if not active:
    return self._mono('没有找到你当前加入的群聊游戏世界。请先在目标群聊中发送 /弹丸 加入。')
   game_room=str(active['room']); gr=s.room(game_room)
   if not gr['started']: return self._mono('当前群聊游戏尚未开始。')
   if not active['alive']: return self._mono('已淘汰的玩家不能提交杀人申请。')
   if gr['paused']: return self._mono('当前班级处于暂停状态，暂时不能提交申请。')
   if gr['case_json']: return self._mono('当前班级已有案件正在处理，不能叠加新的杀人申请。')
   db.execute('INSERT INTO pending_kill_requests(uid,room,created) VALUES(?,?,?) ON CONFLICT(uid) DO UPDATE SET room=excluded.room,created=excluded.created',(uid,game_room,int(time.time())))
   s.save()
   return self._mono('秘密申请已进入待填写状态。请在本私聊中单独发送目标玩家的 QQ 号（纯数字）。目标必须已经加入你当前群聊的游戏世界，不能填写自己。')

  if a=='搜查':
   if not r['case_json']: return self._mono('当前没有已建立的案件。')
   db.execute('UPDATE rooms SET phase="搜查" WHERE room=?',(room,)); return self._mono('搜查阶段开始！黑白熊已经封锁现场。输入 /弹丸 探索 逐步收集案件证据；输入 /弹丸 证据 查看已发现内容。')
  if a=='案件':
   case=json.loads(r['case_json'] or '{}')
   if not case: return self._mono('当前没有正在处理的案件。')
   found=db.execute('SELECT COUNT(*) FROM evidence WHERE room=?',(room,)).fetchone()[0]
   return self._mono(f'【案件状态】\n被害者：{case.get("victim","未知")}\n案发地点：{case.get("scene","未知")}\n当前阶段：{r["phase"]}\n已发现证据：{found}/{len(case.get("evidence",[]))}\n（凶手身份为隐藏事实，不会在案件状态中显示。）')
  if a=='证词':
   case=json.loads(r['case_json'] or '{}')
   if not case: return self._mono('当前没有可查看的案件证词。')
   return self._mono('【证词记录】\n'+('\n'.join(f'{i+1}. {v}' for i,v in enumerate(case.get('statements',[]))) or '目前尚未取得有效证词。'))
  if a=='证据':
   rows=db.execute('SELECT evidence,detail FROM evidence WHERE room=?',(room,)).fetchall()
   return self._mono('【案件证据】\n'+('\n'.join(f'• {z["evidence"]}：{z["detail"]}' for z in rows) if rows else '目前没有已发现证据。'))
  if a=='推理':
   if not x: return self._mono('用法：/弹丸 推理 你的推理内容')
   case=json.loads(r['case_json'] or '{}')
   if not case: return self._mono('当前没有案件可供推理。')
   text=' '.join(x)
   key=case.get('solution_keywords',[])
   hits=[k for k in key if k in text]
   reward=''
   if hits:
    earned,_=self._award_coins(room,uid,f'trial_reasoning:{case.get("created",r["chapter"])}',(20,40))
    if earned: reward=f'\n学级裁判推理奖励：黑白熊币 +{earned}。'
   return self._mono(('你的推理触及了关键方向：'+'、'.join(hits)+'。' if hits else '目前还没有命中已锁定的关键矛盾。')+reward+'\n请结合 /弹丸 证据 继续推理。')
  if a=='学级裁判':
   if not r['case_json']: return self._mono('没有案件，裁判也就无从开始。')
   db.execute('UPDATE rooms SET phase="学级裁判" WHERE room=?',(room,)); return self._mono('学级裁判开始！请使用 /弹丸 推理 内容 发表观点，或 /弹丸 投票 角色名。')
  if a=='处刑':
   case=json.loads(r['case_json'] or '{}')
   if not case or r['phase']!='处刑': return self._mono('还没有进入处刑阶段。请先完成学级裁判并正确投票。')
   culprit=case.get('culprit','')
   db.execute('UPDATE players SET alive=0 WHERE room=? AND name=?',(room,culprit))
   cleared_chapter=int(r['chapter'])
   db.execute('UPDATE rooms SET phase="日常生活",case_json="",chapter=chapter+1,day=1 WHERE room=?',(room,))
   db.execute('DELETE FROM evidence WHERE room=?',(room,)); db.execute('DELETE FROM votes WHERE room=?',(room,))
   chapter_reward=self._award_room_coins(room,f'chapter:{cleared_chapter}',self.rng.choice((50,60,70,80,90,100)))
   return self._mono(f'【处刑完成】{culprit} 已从本次模拟游戏中淘汰。案件资料已归档清理，游戏进入第{cleared_chapter+1}章。\n章节通关奖励：全班共享黑白熊币 +{chapter_reward}。此处刑为插件原创文本事件，不复刻原作演出。')
  if a=='投票':
   if r['phase']!='学级裁判': return self._mono('当前不在学级裁判投票阶段。请先输入 /弹丸 学级裁判。')
   if not x: return self._mono('用法：/弹丸 投票 角色名')
   target=' '.join(x)
   valid_targets=ROSTERS[r['world']]+[z['name'] for z in db.execute('SELECT name FROM players WHERE room=?',(room,)).fetchall()]
   if target not in valid_targets: return self._mono('投票对象不在当前世界名册或玩家名单中。')
   db.execute('INSERT INTO votes(room,uid,target) VALUES(?,?,?) ON CONFLICT(room,uid) DO UPDATE SET target=excluded.target',(room,uid,target))
   votes=db.execute('SELECT target,COUNT(*) AS n FROM votes WHERE room=? GROUP BY target ORDER BY n DESC',(room,)).fetchall()
   total=db.execute('SELECT COUNT(*) FROM players WHERE room=? AND alive=1',(room,)).fetchone()[0]
   cast=db.execute('SELECT COUNT(*) FROM votes WHERE room=?',(room,)).fetchone()[0]
   if total>0 and cast>=total and r['case_json']:
    case=json.loads(r['case_json']); top=votes[0]['n'] if votes else 0
    leaders=[z['target'] for z in votes if z['n']==top]
    if len(leaders)>1:
     db.execute('DELETE FROM votes WHERE room=?',(room,))
     return self._mono('投票出现平票！学级裁判暂不结束。请继续讨论后重新投票。')
    winner=leaders[0] if leaders else ''
    if winner==case.get('culprit'):
     db.execute('UPDATE rooms SET phase="处刑" WHERE room=?',(room,))
     earned,_=self._award_coins(room,uid,f'trial_vote:{case.get("created",r["chapter"])}',(20,50))
     return self._mono(f'投票结束！全班投票结果指向：{winner}。\n正确！黑白熊确认其为本案凶手。被害者：{case["victim"]}。你的正确投票奖励：黑白熊币 +{earned}。进入处刑阶段：/弹丸 处刑')
    db.execute('DELETE FROM votes WHERE room=?',(room,))
    return self._mono(f'投票结束！多数票指向：{winner}。\n……哎呀，看来你们判断失误了。裁判暂不结束，投票记录已清空，可以继续讨论并重新投票。')
   return self._mono(f'已记录你的投票：{target}。当前投票数：{cast}/{total}。')
  if a=='地图': return self._mono('【当前世界地图】\n'+'\n'.join(f'{i+1}. {loc}' for i,loc in enumerate(LOCATIONS[r['world']]))+'\n使用 /弹丸 前往 地点 移动。')
  if a=='羁绊':
   rows=db.execute('SELECT character,value FROM bonds WHERE room=? AND uid=? ORDER BY value DESC',(room,uid)).fetchall()
   return self._mono('【羁绊记录】\n'+('\n'.join(f'{z["character"]}：{z["value"]}/100（{self._bond_stage(z["value"])}）' for z in rows) if rows else '尚未建立羁绊。使用 /弹丸 自由行动 角色名 开始。'))
  if a=='章节': return self._mono(f'第{r["chapter"]}章｜第{r["day"]}天｜{r["phase"]}。')
  if a=='日常事件':
   if not r['started']: return self._mono('请先开始游戏。')
   event_text=self.rng.choice([f'食堂今天准备了特别菜单。{self.rng.choice(ROSTERS[r["world"]])}似乎对此很感兴趣。',f'{self.rng.choice(ROSTERS[r["world"]])}在{r["location"] or LOCATIONS[r["world"]][0]}附近徘徊，像是在等人。','校园广播突然播放了一段古怪的音乐。'])
   earned,remaining=self._award_coins(room,uid,'daily_event',(20,50))
   reward_text=f'\n日常事件奖励：黑白熊币 +{earned}' if earned else '\n今天的日常事件奖励已领取。'
   return self._mono(event_text+reward_text)
  if a=='希望碎片':
   n=db.execute('SELECT COUNT(*) FROM bonds WHERE room=? AND uid=? AND value>=10',(room,uid)).fetchone()[0]
   return self._mono(f'羁绊记录：{n} 位角色达到认识阶段。')
  if a=='公告': return self._mono(f'【黑白熊公告】当前世界：{WORLD_NAMES[r["world"]]}\\n章节：第{r["chapter"]}章\\n阶段：{r["phase"]}\\nうぷぷぷ！请各位学生继续努力活下去哦！')
  if a=='帮助': return MENU
  return self._mono('没有这个功能。输入 /弹丸 菜单 查看完整菜单。')

 def _talent(self,name,uid):
  # 首次建档时从跨领域才能池中等概率随机抽取；抽取结果写入 players.talent 持久化。
  options=[
   # 学术、研究与知识领域
   '超高校级的数学家','超高校级的物理学家','超高校级的化学家','超高校级的生物学家',
   '超高校级的天文学家','超高校级的历史学家','超高校级的考古学家','超高校级的语言学家',
   '超高校级的心理学家','超高校级的哲学家','超高校级的医学家','超高校级的药剂师',
   '超高校级的法学家','超高校级的经济学家','超高校级的气象学家','超高校级的博物学家',
   # 艺术、设计与创作领域
   '超高校级的画家','超高校级的漫画家','超高校级的小说家','超高校级的诗人',
   '超高校级的插画师','超高校级的摄影师','超高校级的影像制作者','超高校级的导演',
   '超高校级的作曲家','超高校级的钢琴家','超高校级的小提琴家','超高校级的歌手',
   '超高校级的舞者','超高校级的演员','超高校级的声优','超高校级的魔术师',
   '超高校级的服装设计师','超高校级的建筑师','超高校级的花艺师','超高校级的工艺师',
   # 体育、竞技与户外领域
   '超高校级的短跑选手','超高校级的体操选手','超高校级的游泳选手','超高校级的花样滑冰选手',
   '超高校级的网球选手','超高校级的乒乓球选手','超高校级的羽毛球选手','超高校级的篮球选手',
   '超高校级的足球选手','超高校级的击剑选手','超高校级的弓道选手','超高校级的攀岩者',
   '超高校级的棋手','超高校级的赛车手','超高校级的滑板选手','超高校级的登山家',
   # 生活技能、手艺与服务领域
   '超高校级的料理人','超高校级的甜点师','超高校级的面包师','超高校级的调酒师',
   '超高校级的裁缝','超高校级的理发师','超高校级的园艺师','超高校级的兽医',
   '超高校级的训兽师','超高校级的护理师','超高校级的消防员','超高校级的急救员',
   '超高校级的侦探','超高校级的记者','超高校级的外交官','超高校级的教师',
   # 科技、工程与现代职业领域
   '超高校级的程序员','超高校级的黑客','超高校级的机器人研究者','超高校级的发明家',
   '超高校级的工程师','超高校级的机械师','超高校级的飞行员','超高校级的宇航员',
   '超高校级的游戏开发者','超高校级的网络主播','超高校级的情报分析师','超高校级的密码学家',
   # 社会、表演与特殊才能
   '超高校级的企业家','超高校级的谈判专家','超高校级的占卜师','超高校级的幸运儿',
   '超高校级的生存专家','超高校级的记忆大师','超高校级的模仿达人','超高校级的收藏家',
   '超高校级的鉴定师','超高校级的园区导览员','超高校级的偶像','超高校级的喜剧演员',
   '超高校级的观察者','超高校级的推理家','超高校级的战略家','超高校级的心理咨询师',
  ]
  return self.rng.choice(options)
 def _ensure_char(self,world,ch):
  if ch not in ROSTERS[world]: raise ValueError('角色不在当前世界')
 def _bond(self,room,uid,ch):
  row=self.store.db.execute('SELECT value FROM bonds WHERE room=? AND uid=? AND character=?',(room,uid,ch)).fetchone(); return row['value'] if row else 0
 def _grant_bond_underwear(self,room,uid,ch,value):
  """Grant one character-specific keepsake the first time affection reaches 100."""
  if value < 100:
   return False
  db=self.store.db
  cur=db.execute('INSERT OR IGNORE INTO bond_rewards(room,uid,character,granted_at) VALUES(?,?,?,?)',(room,uid,ch,int(time.time())))
  if not cur.rowcount:
   return False
  db.execute('INSERT INTO inventory(room,uid,item,category,amount) VALUES(?,?,?,"羁绊纪念品",1) ON CONFLICT(room,uid,item,category) DO UPDATE SET amount=amount+1',(room,uid,f'{ch}的内裤'))
  self.store.save()
  return True
 def _character_card(self,world,ch):
  if ch not in ROSTERS[world]: return self._mono('当前世界名册中没有这名角色。')
  return self._mono(f'【{ch}】\n所属作品：{WORLD_NAMES[world]}')
 async def _plan_case(self,event,world,applicant,victim,scene):
  """Ask the active chat model for a bounded case plan; validate the structure before locking it."""
  fallback={
   'method':'凶手利用现场可移动物品制造了错误的案发时间判断。',
   'timeline':['案发前，凶手确认现场无人。','案发时，凶手实施计划并离开。','发现尸体后，凶手试图用证词掩盖行动时间。'],
   'weapon':'现场可移动物品（待调查确认）',
   'evidence':[
    {'name':'现场足迹','detail':f'{scene}附近留下了与案发时间相关的鞋印。'},
    {'name':'时间记录','detail':'现场时间记录与一名学生的证词存在偏差。'},
    {'name':'破损物品','detail':f'{scene}发现一件带有新鲜损坏痕迹的物品。'},
    {'name':'目击记录','detail':'一名学生提供了案发前后的目击信息。'}],
   'statements':['我在案发时一直待在自己的房间。','我只是在走廊短暂停留，没有进入现场。'],
   'solution_keywords':[applicant,victim,scene,'时间','足迹'],
   'contradiction':'证词所称的时间与现场记录、足迹出现的时间无法同时成立。'
  }
  try:
   umo=getattr(event,'unified_msg_origin',None)
   provider_id=await self.context.get_current_chat_provider_id(umo) if umo else None
   if not provider_id: return fallback
   prompt=(f'为《{WORLD_NAMES[world]}》生成一宗插件原创、可推理的模拟案件。固定申请者/真实凶手={applicant}，被害者={victim}，案发地点={scene}。只能使用当前作品角色和地点。返回纯JSON对象，字段：method(简短作案方式), timeline(3-5条按时间顺序), weapon(物品), evidence(至少4条，每条含name/detail), statements(至少2条证词), solution_keywords(至少4个推理关键词), contradiction(核心矛盾)。线索必须能支持真相，不能出现超自然、瞬移、凭空替身、无法解释的换装或与地点不符的物理行为。不要改变固定凶手和被害者。不要添加 markdown。')
   resp=await self.context.llm_generate(chat_provider_id=provider_id,prompt=prompt,system_prompt='你是案件设计器。只输出合法JSON。案件必须公平可解，线索之间一致。')
   raw=(getattr(resp,'completion_text',None) or getattr(resp,'text',None) or '').strip()
   if not raw: return fallback
   left=raw.find('{'); right=raw.rfind('}')
   data=json.loads(raw[left:right+1])
   if not isinstance(data.get('evidence'),list) or len(data['evidence'])<4: return fallback
   if not isinstance(data.get('timeline'),list) or len(data['timeline'])<3: return fallback
   if not isinstance(data.get('solution_keywords'),list) or len(data['solution_keywords'])<3: return fallback
   if any(not isinstance(z,dict) or not z.get('name') or not z.get('detail') for z in data['evidence']): return fallback
   data['evidence']=data['evidence'][:8]
   data['timeline']=data['timeline'][:6]
   data['statements']=data.get('statements',[])[:6]
   data['solution_keywords']=list(dict.fromkeys([applicant,victim,scene]+[str(k) for k in data['solution_keywords']]))[:12]
   return data
  except Exception as e:
   logger.warning('AI案件规划失败，使用规则案件模板：%s',e)
   return fallback
 async def _chat(self,event,room,uid,ch,msg):
  db=self.store.db
  world=self.store.room(room)['world']
  if ch not in ROSTERS[world]:
   return self._mono('当前世界名册中没有这名角色，已阻止跨作品角色互动。')
  row=db.execute('SELECT value FROM bonds WHERE room=? AND uid=? AND character=?',(room,uid,ch)).fetchone()
  affection=row['value'] if row else 0
  stage=self._bond_stage(affection)
  private=self._private(event)
  # Private conversations may use the user's own group + private history. Group replies
  # only use public group history, never private-chat content.
  visibility_clause='' if private else ' AND is_private=0 AND room=?'
  memory_params=(world,uid,ch) if private else (world,uid,ch,room)
  memory_rows=db.execute('SELECT role,content FROM character_memory_logs WHERE world=? AND uid=? AND character=?'+visibility_clause+' ORDER BY created DESC,rowid DESC LIMIT 10',memory_params).fetchall()
  if not memory_rows:
   legacy=db.execute('SELECT role,content FROM chat_memory WHERE room=? AND uid=? AND character=? ORDER BY created DESC LIMIT 8',(room,uid,ch)).fetchall()
   memory_rows=legacy
  memory_meta=db.execute('SELECT interaction_count FROM character_memories WHERE world=? AND uid=? AND character=?',(world,uid,ch)).fetchone()
  if memory_rows:
   history_text='\n'.join(f'{"玩家" if h["role"]=="user" else ch}：{h["content"]}' for h in reversed(memory_rows))
  elif memory_meta and int(memory_meta['interaction_count'] or 0)>0:
   history_text=f'你们此前已经互动过约{int(memory_meta["interaction_count"])}次，但当前群没有可引用的公开话题。可以自然表现出认识对方，不得提及其他群或私聊中的具体内容。'
  else:
   history_text='暂无；这是自然认识或初次互动，不得假装熟识。'
  player=db.execute('SELECT name FROM players WHERE room=? AND uid=?',(room,uid)).fetchone()
  player_name=player['name'] if player else uid
  prompt=(f'玩家姓名：{player_name}\n当前世界：{WORLD_NAMES[world]}（作品标识：{world}）\n当前作品允许出现的学生角色：{"、".join(ROSTERS[world])}\n角色：{ch}\n关系阶段：{stage}（好感度{affection}/100）\n此前与这名玩家的可用互动记忆：\n{history_text or "暂无；这是自然认识或初次互动，不得假装熟识"}\n本次场景/玩家发言：{msg}\n\n请直接以该角色身份用中文回应。必须严格按以下格式输出，每个部分单独占一行，不得合并成逗号分隔的一行：\n第一行：**【{ch}】**\n第二行：可选的一句简短动作描写，使用（……）。没有必要动作时省略。\n之后：每句台词单独一行，并使用「……」包裹。\n普通回应1～3句、约20～60字；特殊情绪或事件最多约100字。禁止在角色名后追加逗号、重复角色名或把动作和台词接在同一行。不要连续堆叠动作、心理和形容词，不要重复表达同一情绪。只扮演当前角色，不要替其他角色发言；不得提及当前作品名册以外的弹丸角色。不要编造玩家没有说过的个人经历或承诺。')
  system='你是弹丸论破互动模拟器的角色扮演引擎。必须严格遵守当前作品边界，只能演绎指定角色。不得让DR1、DR2、V3角色串场。输出必须是多行结构：加粗角色名独占一行；动作描写单独一行；每句台词单独一行并用「」包裹。绝不把角色名、动作和台词用逗号拼成一行。表达简洁自然，避免小说式长篇动作和心理描写。游戏事实由程序决定；不确定的官方设定不要编造。'
  answer=''
  try:
   umo=getattr(event,'unified_msg_origin',None)
   provider_id=await self.context.get_current_chat_provider_id(umo) if umo else None
   if provider_id:
    resp=await self.context.llm_generate(chat_provider_id=provider_id,prompt=prompt,system_prompt=system)
    answer=(getattr(resp,'completion_text',None) or getattr(resp,'text',None) or str(resp)).strip()
  except Exception as e:
   logger.warning('弹丸角色LLM调用失败，回退到保底台词：%s',e)
  if not answer:
   answer=f'「嗯……我听到了。关于“{msg[:40]}”，我想再多了解一点。」'
  # Hard guard against cross-title named-character leakage from model output.
  foreign=[name for other_world,names in ROSTERS.items() if other_world!=world for name in names]
  if any(name in answer for name in foreign):
   logger.warning('角色回复触发跨作品角色名校验，已回退。world=%s character=%s',world,ch)
   answer='「……先把眼前的事情说清楚吧。我会认真听你说。」'
  answer=answer.strip()
  # Keep role output compact even when the connected model ignores the length instruction.
  if len(answer)>180:
   cut=max(answer.rfind('。',0,170),answer.rfind('！',0,170),answer.rfind('？',0,170),answer.rfind('\n',0,170))
   answer=answer[:cut+1].rstrip() if cut>50 else answer[:170].rstrip()+'……'
  answer=self._format_role_dialogue(ch,answer)
  now=int(time.time())
  db.execute('INSERT INTO chat_memory(room,uid,character,role,content,created) VALUES(?,?,?,?,?,?)',(room,uid,ch,'user',msg,now))
  db.execute('INSERT INTO chat_memory(room,uid,character,role,content,created) VALUES(?,?,?,?,?,?)',(room,uid,ch,'assistant',answer,now+1))
  db.execute('INSERT INTO character_memory_logs(world,uid,character,role,content,created,room,is_private) VALUES(?,?,?,?,?,?,?,?)',(world,uid,ch,'user',msg,now,room,1 if private else 0))
  db.execute('INSERT INTO character_memory_logs(world,uid,character,role,content,created,room,is_private) VALUES(?,?,?,?,?,?,?,?)',(world,uid,ch,'assistant',answer,now+1,room,1 if private else 0))
  db.execute('INSERT INTO character_memories(world,uid,character,first_seen,last_seen,interaction_count) VALUES(?,?,?,?,?,1) ON CONFLICT(world,uid,character) DO UPDATE SET last_seen=excluded.last_seen,interaction_count=character_memories.interaction_count+1',(world,uid,ch,now,now))
  db.execute('DELETE FROM chat_memory WHERE rowid IN (SELECT rowid FROM chat_memory WHERE room=? AND uid=? AND character=? ORDER BY created DESC LIMIT -1 OFFSET 24)',(room,uid,ch))
  db.execute('DELETE FROM character_memory_logs WHERE rowid IN (SELECT rowid FROM character_memory_logs WHERE world=? AND uid=? AND character=? ORDER BY created DESC,rowid DESC LIMIT -1 OFFSET 60)',(world,uid,ch))
  self.store.save()
  return answer
 def _award_coins(self,room,uid,claim_key,reward_range):
  """按事件键去重、按区间随机发币；不设置每日累计上限。"""
  db=self.store.db; today=self._now().strftime('%Y-%m-%d')
  exists=db.execute('SELECT 1 FROM coin_reward_claims WHERE room=? AND uid=? AND claim_key=? AND claim_date=?',(room,uid,claim_key,today)).fetchone()
  if exists: return 0,None
  low,high=map(int,reward_range)
  amount=self.rng.randint(low,high)
  db.execute('INSERT INTO coin_reward_claims(room,uid,claim_key,claim_date,amount) VALUES(?,?,?,?,?)',(room,uid,claim_key,today,amount))
  db.execute('UPDATE rooms SET coins=coins+? WHERE room=?',(amount,room))
  return amount,None

 def _progress_commission(self,room,uid,action):
  db=self.store.db; today=self._now().strftime('%Y-%m-%d')
  row=db.execute('SELECT task,done FROM coin_commissions WHERE room=? AND uid=? AND day=?',(room,uid,today)).fetchone()
  if not row or row['done']: return False
  matched={'自由行动一次':'free','探索地点一次':'explore','触发日常事件一次':'daily'}.get(row['task'])==action
  if not matched: return False
  db.execute('UPDATE coin_commissions SET done=1 WHERE room=? AND uid=? AND day=?',(room,uid,today))
  return True

 def _award_room_coins(self,room,event_key,amount):
  """章节通关奖励按房间事件去重，避免重复执行时重复发币。"""
  db=self.store.db
  cur=db.execute('INSERT OR IGNORE INTO coin_reward_events(room,event_key,amount,created) VALUES(?,?,?,?)',(room,event_key,int(amount),int(time.time())))
  if cur.rowcount:
   db.execute('UPDATE rooms SET coins=coins+? WHERE room=?',(int(amount),room))
   return int(amount)
  return 0

 def _bond_stage(self,value):
  return '陌生' if value<10 else '认识' if value<30 else '友好' if value<50 else '亲密' if value<75 else '挚友'
 def _claim_bond_scene(self,room,uid,ch,before,after):
  thresholds=(10,30,50,75)
  for threshold in thresholds:
   if before < threshold <= after:
    cur=self.store.db.execute('INSERT OR IGNORE INTO bond_scenes(room,uid,character,stage,unlocked_at) VALUES(?,?,?,?,?)',(room,uid,ch,threshold,int(time.time())))
    self.store.save()
    if cur.rowcount: return threshold
  return None
 def _snapshot(self,room):
  d=self.store.db
  tables=['rooms','players','bonds','inventory','evidence','votes','private_actions','chat_memory','room_targets','coin_reward_claims','coin_reward_events','coin_commissions','character_memory_logs','bond_scenes','bond_rewards']; out={}
  for t in tables:
   cols=[z['name'] for z in d.execute(f'PRAGMA table_info({t})')]
   if t=='rooms': cols=[c for c in cols if c!='saved_json']
   names=','.join(cols)
   rows=[dict(z) for z in d.execute(f'SELECT {names} FROM {t} WHERE room=?',(room,))]
   out[t]={'cols':cols,'rows':rows}
  return out
 def _restore(self,room,snap):
  d=self.store.db
  current=d.execute('SELECT saved_json FROM rooms WHERE room=?',(room,)).fetchone()
  saved=current['saved_json'] if current else ''
  for t,info in snap.items():
   if t not in ('rooms','players','bonds','inventory','evidence','votes','private_actions','chat_memory','room_targets','coin_reward_claims','coin_reward_events','coin_commissions','character_memory_logs','bond_scenes','bond_rewards'): continue
   d.execute(f'DELETE FROM {t} WHERE room=?',(room,))
   cols=info['cols']; marks=','.join('?' for _ in cols); names=','.join(cols)
   for row in info['rows']: d.execute(f'INSERT INTO {t} ({names}) VALUES ({marks})',[row.get(c) for c in cols])
  d.execute('UPDATE rooms SET saved_json=? WHERE room=?',(saved,room))
  d.commit()
 async def _admin(self,event,room,r,x):
  if not self._is_admin(event): return self._mono('管理员权限不足。')
  if not x: return self._mono('用法：/弹丸 管理 暂停|继续|重置|播报设置 开/关|角色互动 开/关|播报测试|触发事件 日常/突发|备份|恢复 文件名')
  op=x[0]; d=self.store.db
  if op=='暂停': d.execute('UPDATE rooms SET paused=1 WHERE room=?',(room,)); return self._mono('本房间游戏已暂停。')
  if op=='继续': d.execute('UPDATE rooms SET paused=0 WHERE room=?',(room,)); return self._mono('本房间游戏继续。')
  if op=='重置':
   for t in ('players','bonds','inventory','evidence','votes','private_actions','chat_memory','coin_reward_claims','coin_reward_events','coin_commissions','character_memory_logs','bond_scenes','bond_rewards'): d.execute(f'DELETE FROM {t} WHERE room=?',(room,))
   d.execute('UPDATE rooms SET started=0,paused=0,chapter=1,day=1,phase="日常生活",case_json="",coins=100 WHERE room=?',(room,)); self.store.save(); return self._mono('本房间当前世界已重置；其他世界数据保留。')
  if op=='播报设置':
   if len(x)<2 or x[1] not in ('开','关','on','off','开启','关闭'): return self._mono('用法：/弹丸 管理 播报设置 开/关')
   val=1 if x[1] in ('开','on','开启') else 0
   d.execute('UPDATE rooms SET broadcast=? WHERE room=?',(val,room)); self.store.save()
   return self._mono('本群当前世界的自动播报已'+('开启' if val else '关闭')+'。')
  if op=='角色互动':
   if len(x)<2 or x[1] not in ('开','关','on','off','开启','关闭'): return self._mono('用法：/弹丸 管理 角色互动 开/关')
   val=1 if x[1] in ('开','on','开启') else 0
   d.execute('UPDATE rooms SET character_broadcast=? WHERE room=?',(val,room)); self.store.save()
   return self._mono('本群当前世界的随机学生角色主动互动已'+('开启' if val else '关闭')+'。普通黑白熊播报不受影响。')
  if op=='播报测试': return await self._broadcast_room(room,'test')
  if op=='触发事件':
   typ=x[1] if len(x)>1 else '日常'
   return await self._broadcast_room(room,'event' if typ in ('突发','事件') else 'daily')
  if op=='备份':
   fn='backup_'+re.sub(r'[^a-zA-Z0-9_-]','_',room)+'.json'
   (BACKUP_DIR/fn).write_text(json.dumps(self._snapshot(room),ensure_ascii=False,indent=2),encoding='utf-8')
   return self._mono('房间备份已保存至 AstrBot plugin_data/danganronpa_simulator/backups：'+fn)
  if op=='恢复':
   if len(x)<2: return self._mono('用法：/弹丸 管理 恢复 backup_房间标识.json')
   fn=Path(x[1]).name
   if not fn.startswith('backup_') or not fn.endswith('.json'): return self._mono('只允许恢复插件生成的 backup_*.json 文件。')
   fp=BACKUP_DIR/fn
   if not fp.is_file(): return self._mono('找不到该备份文件：'+fn)
   try:
    payload=json.loads(fp.read_text(encoding='utf-8'))
    if 'rooms' not in payload or not any(z.get('room')==room for z in payload['rooms']['rows']): return self._mono('备份不属于当前房间，拒绝恢复。')
    self._restore(room,payload); return self._mono('已恢复当前房间备份：'+fn)
   except Exception as e: return self._mono('备份校验失败，未执行恢复：'+str(e))
  return self._mono('未知管理操作。')

 def _cfg(self,key,default):
  try:
   value=self.config.get(key,default)
   return default if value is None else value
  except Exception: return default

 def _now(self):
  name=str(self._cfg('timezone','Asia/Shanghai'))
  try: return datetime.now(ZoneInfo(name))
  except (ZoneInfoNotFoundError,ValueError):
   logger.warning('弹丸插件时区配置无效：%s，改用服务器本地时区。',name)
   return datetime.now().astimezone()

 def _quiet(self,now):
  try:
   sh,sm=[int(v) for v in str(self._cfg('quiet_hours_start','23:00')).split(':')]
   eh,em=[int(v) for v in str(self._cfg('quiet_hours_end','08:00')).split(':')]
   cur=now.hour*60+now.minute; a=sh*60+sm; b=eh*60+em
   return (a<=cur<b) if a<b else (cur>=a or cur<b) if a!=b else False
  except Exception:
   logger.warning('弹丸插件静默时段格式错误，已忽略静默时段。'); return False

 def _broadcast_content(self,row,kind):
  world=row['world']
  if kind=='test':
   return self._mono('主动播报测试：这条消息由后台/管理指令通过 AstrBot 主动消息接口发送。收到这条消息即表示目标会话发送链路已通。')
  if kind=='event':
   body=self.rng.choice(['校园广播：刚刚在走廊尽头发现了一个没有署名的包裹。请各位学生不要擅自拆开……才怪！','突发通知：校内某处传来奇怪的声响。想知道发生了什么，就自己去调查吧！うぷぷぷ！','黑白熊公告：本校今日追加一项特别活动。规则嘛，等你们亲自发现就知道了！'])
  elif kind=='case':
   body='非日常时间到了！请各位学生留意搜查与证据，学级裁判即将开始。不要迟到哦！'
  elif kind=='activity':
   body=self.rng.choice(['扭蛋机补充了新一批奖品！想要好东西的话，就拿黑白熊币来试试手气吧！','自由行动时间开始！去找当前世界的学生聊聊，建立你们自己的羁绊吧！','校园活动通知：今天也可以探索地点、寻找线索，或者试试扭蛋机哦！'])
  else:
   body=self.rng.choice(['日常广播：今天也请各位学生努力享受校园生活。至于“希望”嘛……唔噗噗！','食堂通知：今天的气氛似乎格外热闹。去看看有什么新鲜事吧！','黑白熊提醒：自由行动时间正在继续。找喜欢的角色聊聊，说不定会有意外收获哦！'])
  return self._mono(f'【{WORLD_NAMES.get(world,"希望之峰学园")} · 第{row["chapter"]}章 · 第{row["day"]}天】\n{body}')

 async def _student_dynamic_content(self,row,umo):
  """A short campus-life update featuring one student from the active title."""
  room_id=row['room']
  selected_world=room_id.rsplit('::',1)[-1] if '::' in room_id else row['world']
  world=selected_world if selected_world in WORLD_NAMES else row['world']
  roster=ROSTERS.get(world,[])
  if not roster:
   return self._broadcast_content(row,'daily')
  character=self.rng.choice(roster)
  location=row['location'] if 'location' in row.keys() and row['location'] else self.rng.choice(LOCATIONS[world])
  answer=''
  try:
   provider_id=await self.context.get_current_chat_provider_id(umo) if umo else None
   if provider_id:
    prompt=(f'当前作品：{WORLD_NAMES[world]}（{world}）\n允许出现的学生角色名单：{"、".join(roster)}\n本条动态主角：{character}\n场景：{location}\n写一条简短的校园日常动态，像电子学生手册播报某位学生正在做什么。保持角色基本性格，不编造剧情关键事实、案件真相或其他角色互动。只出现主角本人，不要提及名单外的弹丸角色。格式为【{character}】开头，1～2句，约20～50字。')
    resp=await self.context.llm_generate(chat_provider_id=provider_id,prompt=prompt,system_prompt='你是弹丸论破校园动态播报器。严格限制在指定作品和指定角色，不得跨作品串场。内容简短、日常，不写长篇小说。')
    answer=(getattr(resp,'completion_text',None) or getattr(resp,'text',None) or str(resp)).strip()
  except Exception as e:
   logger.warning('弹丸学生动态LLM调用失败，使用简短模板：%s',e)
  foreign=[name for other_world,names in ROSTERS.items() if other_world!=world for name in names]
  other_current=[name for name in roster if name!=character]
  if not answer or any(name in answer for name in foreign+other_current):
   answer=f'【{character}】\n（在{location}附近停留，似乎正忙着自己的事情。）'
  else:
   answer=re.sub(rf'^【{re.escape(character)}】\s*','',answer).strip()
   if len(answer)>130:
    cut=max(answer.rfind('。',0,120),answer.rfind('！',0,120),answer.rfind('？',0,120),answer.rfind('\n',0,120))
    answer=answer[:cut+1].rstrip() if cut>30 else answer[:120].rstrip()+'……'
   answer=f'【{character}】\n{answer}'
  answer=self._format_role_dialogue(character,answer)
  return self._mono(f'【{WORLD_NAMES[world]} · 学生动态】\n{answer}')

 async def _character_broadcast_content(self,row,umo):
  """Generate one short proactive line from the active world's roster only."""
  room_id=row['room']
  selected_world=room_id.rsplit('::',1)[-1] if '::' in room_id else row['world']
  world=selected_world if selected_world in WORLD_NAMES else row['world']
  roster=ROSTERS.get(world,[])
  if not roster:
   return self._broadcast_content(row,'daily')
  players=self.store.db.execute('SELECT uid,name FROM players WHERE room=? AND alive=1 ORDER BY RANDOM() LIMIT 1',(row['room'],)).fetchone()
  if not players:
   return self._broadcast_content(row,'daily')
  character=self.rng.choice(roster)
  uid=str(players['uid']); player_name=players['name'] or uid
  hist=self.store.db.execute('SELECT role,content FROM character_memory_logs WHERE world=? AND uid=? AND character=? AND room=? AND is_private=0 ORDER BY created DESC,rowid DESC LIMIT 6',(world,uid,character,row['room'])).fetchall()
  history='\n'.join(f'{"玩家" if z["role"]=="user" else character}：{z["content"]}' for z in reversed(hist)) or '此前没有与该玩家互动过；这是第一次自然搭话，不得假装熟悉。'
  answer=''
  try:
   provider_id=await self.context.get_current_chat_provider_id(umo) if umo else None
   if provider_id:
    prompt=(f'当前作品：{WORLD_NAMES[world]}（{world}）\n本作品唯一允许出现的学生角色名单：{"、".join(roster)}\n发言角色：{character}\n群成员：{player_name}\n与该成员在本群的公开互动记忆：\n{history}\n当前游戏：第{row["chapter"]}章、第{row["day"]}天、{row["phase"]}。\n请写一条角色主动发言，像角色偶尔在群里主动找这位成员说话。可以打招呼、吐槽、关心、接续公开话题或自言自语，不必每次提问。必须符合角色性格，不得编造不存在的共同经历；没有记忆就自然初次搭话。\n必须严格按多行格式输出：第一行 **【{character}】**；可选的简短动作描写单独一行，用（……）；之后每句台词各占一行，并用「……」包裹。禁止用逗号把角色名、动作和台词拼成一行。1～3句，约20～60字。只能出现指定角色，不要提及名单以外的弹丸角色。')
    resp=await self.context.llm_generate(chat_provider_id=provider_id,prompt=prompt,system_prompt='你是弹丸论破角色演绎引擎。严格锁定指定作品和指定角色，不得跨作品串场。必须将加粗角色名、动作、每句台词分别放在独立行；不得用逗号拼接。用简洁自然的群聊发言，不写长篇小说。')
    answer=(getattr(resp,'completion_text',None) or getattr(resp,'text',None) or str(resp)).strip()
  except Exception as e:
   logger.warning('弹丸主动角色播报LLM调用失败，使用短保底发言：%s',e)
  foreign=[name for other_world,names in ROSTERS.items() if other_world!=world for name in names]
  other_current=[name for name in roster if name!=character]
  if not answer or any(name in answer for name in foreign+other_current):
   answer=f'【{character}】\n「{player_name}，现在有空吗？我刚好想找个人说说话。」'
  else:
   # Normalize duplicated headers and enforce concise output.
   answer=re.sub(rf'^【{re.escape(character)}】\s*','',answer).strip()
   if len(answer)>150:
    cut=max(answer.rfind('。',0,140),answer.rfind('！',0,140),answer.rfind('？',0,140),answer.rfind('\n',0,140))
    answer=answer[:cut+1].rstrip() if cut>35 else answer[:140].rstrip()+'……'
   answer=f'【{character}】\n{answer}'
  answer=self._format_role_dialogue(character,answer)
  now=int(time.time())
  self.store.db.execute('INSERT INTO character_memory_logs(world,uid,character,role,content,created,room,is_private) VALUES(?,?,?,?,?,?,?,0)',(world,uid,character,'assistant',answer,now,row['room']))
  self.store.db.execute('INSERT INTO character_memories(world,uid,character,first_seen,last_seen,interaction_count) VALUES(?,?,?,?,?,1) ON CONFLICT(world,uid,character) DO UPDATE SET last_seen=excluded.last_seen,interaction_count=character_memories.interaction_count+1',(world,uid,character,now,now))
  self.store.db.execute('DELETE FROM character_memory_logs WHERE rowid IN (SELECT rowid FROM character_memory_logs WHERE world=? AND uid=? AND character=? ORDER BY created DESC,rowid DESC LIMIT -1 OFFSET 60)',(world,uid,character))
  self.store.save()
  return answer

 async def _broadcast_message(self,row,kind):
  if kind=='student':
   return await self._student_dynamic_content(row,row['umo'])
  if kind=='character':
   return await self._character_broadcast_content(row,row['umo'])
  return self._broadcast_content(row,kind)
 async def _broadcast_room(self,room,kind='daily'):
  target=self.store.db.execute('SELECT umo FROM room_targets WHERE room=?',(room,)).fetchone()
  if not target or not target['umo']: return self._mono('没有已登记的群会话地址。请先在目标群发送一次 /弹丸 帮助。')
  try:
   message=await self._broadcast_message({**dict(self.store.room(room)), 'room': room, 'umo': target['umo']},kind)
   ok=await self.context.send_message(target['umo'],MessageChain().message(self._pretty_lines(self._format_command_output(message).splitlines())))
   if ok is False: return self._mono('主动播报失败：AstrBot 没有找到该会话对应的平台。请确认平台在线且支持主动消息。')
   now=int(time.time()); today=self._now().strftime('%Y-%m-%d')
   self.store.db.execute('UPDATE room_targets SET last_broadcast_at=?,daily_date=?,daily_count=CASE WHEN daily_date=? THEN daily_count+1 ELSE 1 END WHERE room=?',(now,today,today,room)); self.store.save()
   logger.info('弹丸主动群播报已提交：room=%s kind=%s',room,kind)
   return self._mono('主动播报发送请求已交给 AstrBot 平台。请检查目标群是否收到；失败时查看 AstrBot/NapCat 日志。')
  except Exception as e:
   logger.error('弹丸主动群播报失败 room=%s: %s\n%s',room,e,traceback.format_exc())
   return self._mono(f'主动播报发送失败：{type(e).__name__}: {e}')

 async def _broadcast_loop(self):
  while True:
   try:
    await asyncio.sleep(max(10,int(self._cfg('broadcast_poll_seconds',30))))
    if not bool(self._cfg('auto_broadcast_enabled',True)): continue
    now_dt=self._now()
    if self._quiet(now_dt): continue
    now=int(time.time()); today=now_dt.strftime('%Y-%m-%d')
    interval=max(5,int(self._cfg('broadcast_interval_minutes',180)))*60
    limit=max(1,int(self._cfg('broadcast_daily_limit',4)))
    rows=self.store.db.execute("SELECT r.room,rs.active_world AS world,r.chapter,r.day,r.phase,r.location,r.case_json,r.broadcast,r.character_broadcast,r.started,t.umo,t.last_broadcast_at,t.daily_date,t.daily_count FROM rooms r JOIN room_targets t ON t.room=r.room JOIN room_settings rs ON r.room=rs.base_room || '::' || rs.active_world WHERE r.started=1 AND r.broadcast=1 AND t.umo!=''").fetchall()
    for row in rows:
     if now-int(row['last_broadcast_at'] or 0)<interval: continue
     count=int(row['daily_count'] or 0) if row['daily_date']==today else 0
     if count>=limit: continue
     choices=['daily','daily','event','activity','student']
     weights=[5,2,2,1,2]
     if row['phase']=='学级裁判' or row['case_json']:
      choices.append('case'); weights.append(2)
     if row['character_broadcast']:
      choices.append('character'); weights.append(3)
     kind=self.rng.choices(choices,weights=weights)[0]
     try:
      message=await self._broadcast_message(row,kind)
      ok=await self.context.send_message(row['umo'],MessageChain().message(self._pretty_lines(self._format_command_output(message).splitlines())))
      if ok is False:
       logger.error('弹丸自动播报未发送：平台未匹配 room=%s umo=%s',row['room'],row['umo']); continue
      self.store.db.execute('UPDATE room_targets SET last_broadcast_at=?,daily_date=?,daily_count=? WHERE room=?',(now,today,count+1,row['room']))
      self.store.save(); logger.info('弹丸自动群播报已提交 room=%s kind=%s',row['room'],kind)
     except Exception:
      logger.error('弹丸自动播报异常 room=%s\n%s',row['room'],traceback.format_exc())
   except asyncio.CancelledError: raise
   except Exception:
    logger.error('弹丸播报调度器异常\n%s',traceback.format_exc()); await asyncio.sleep(10)

 async def terminate(self):
  task=getattr(self,'_broadcast_task',None)
  if task:
   task.cancel()
   try: await task
   except asyncio.CancelledError: pass
  try: self.store.db.commit(); self.store.db.close()
  except Exception: pass

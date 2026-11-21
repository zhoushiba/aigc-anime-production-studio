-- AIGC 动漫番剧制作工作台 —— 演示数据（由 scripts/export_db.py 自动导出）
-- 应用启动时会自动写入等价种子（backend/app/services/seed.py），本文件用于快速理解数据形态。

-- users：5 行
INSERT INTO users (id, username, password_hash, display_name, role, created_at) VALUES (1, 'director', 'pbkdf2$120000$66b932654882927bb6722e408426eba0$293e1fbb4deb5441d48a0a1ddfe58901e5e899beb009dd2ae9771d7d14469c7e', '林导', 'director', '2026-11-21 17:09:46.253164');
INSERT INTO users (id, username, password_hash, display_name, role, created_at) VALUES (2, 'storyboard', 'pbkdf2$120000$0cbf76a8ea4859af1cc95d816a51dc5d$7701138e631956658817ba62034cedcd30d291787562dbca34faacc5308a1091', '苏分镜', 'storyboard', '2026-11-21 17:09:46.507981');
INSERT INTO users (id, username, password_hash, display_name, role, created_at) VALUES (3, 'artist', 'pbkdf2$120000$60d7f3118d74bc1f301c43c376c534a6$32990bab86f15f88cca3cd0894a8b410920e883f1f4f3751e9b7fab9470036bd', '阿美术', 'artist', '2026-11-21 17:09:46.773007');
INSERT INTO users (id, username, password_hash, display_name, role, created_at) VALUES (4, 'reviewer', 'pbkdf2$120000$f16abbf56cd2cfbd6d35d68f50f2e228$dbf3fee16e4e4fc719acd6b72e8a0b3673109dbf4c4701af9c0ebf4a4c2b4423', '王审核', 'reviewer', '2026-11-21 17:09:47.076026');
INSERT INTO users (id, username, password_hash, display_name, role, created_at) VALUES (5, 'student', 'pbkdf2$120000$943afc6429e54e8d36fe7af777b757d2$c7c3597bcdef955692b61d2128a63436269a85ee02d68e3904cae51225d6ec8e', '小学员', 'student', '2026-11-21 17:09:47.316041');

-- series：1 行
INSERT INTO series (id, title, genre, logline, synopsis, episodes_planned, target_duration, style, platform, status, cover_prompt, cover_asset_id, owner_id, created_at, updated_at) VALUES (1, '星海拾光', '科幻 / 治愈', '失去记忆的少女与观测员，在星海灯塔上收集散落的光。', '第 1 集《灯塔亮起》：少女林澈在废弃观测站醒来，失去了过往记忆。值班观测员苏眠发现她能与星海 Lighthouse 系统共鸣，两人决定重启灯塔，为即将熄灭的星海补上最后一束光。', 6, 90, '日系赛璐璐', 'vertical', 'in_production', 'star sea lighthouse, girl and observer silhouette, cel shading anime style', 1, 1, '2026-11-21 17:09:47.334040', '2026-11-21 17:09:48.530450');

-- episodes：3 行
INSERT INTO episodes (id, series_id, number, title, summary, status, created_at, updated_at) VALUES (1, 1, 1, '灯塔亮起', '林澈醒来，与苏眠相遇。', 'storyboard', '2026-11-21 17:09:47.338422', '2026-11-21 17:09:47.338422');
INSERT INTO episodes (id, series_id, number, title, summary, status, created_at, updated_at) VALUES (2, 1, 2, '失重的回音', '星海出现异常回波。', 'scripting', '2026-11-21 17:09:47.338422', '2026-11-21 17:09:47.338422');
INSERT INTO episodes (id, series_id, number, title, summary, status, created_at, updated_at) VALUES (3, 1, 3, '最后一束光', '灯塔重启，代价浮现。', 'draft', '2026-11-21 17:09:47.338422', '2026-11-21 17:09:47.338422');

-- scripts：1 行
INSERT INTO scripts (id, episode_id, version, structure, content, is_current, created_by, created_at) VALUES (1, 1, 1, '三幕式', '第一幕 · 建置
夜。废弃观测站。林澈从通讯台前醒来，全息屏幕还亮着上一段留言。

第二幕 · 对抗
苏眠发现灯塔能源只剩 12%，两人尝试用星海回波补能。

第三幕 · 收束
灯塔亮起，林澈的记忆碎片浮现，画面推向星海。', 1, 'director', '2026-11-21 17:09:47.344422');

-- script_scenes：3 行
INSERT INTO script_scenes (id, script_id, episode_id, seq, title, location, time_of_day, characters, action_text, dialogue, mood, duration_seconds, created_at) VALUES (1, 1, 1, 1, '观测站初醒', '废弃观测站', '深夜', '林澈、苏眠', '林澈睁眼，红色的警报灯在墙面上扫过。苏眠推门进来，手里提着应急灯。', '苏眠：你醒了？这台通讯机三年没响过了。
林澈：我……记不起自己的名字。', '悬疑、疏离', 28.0, '2026-11-21 17:09:47.355424');
INSERT INTO script_scenes (id, script_id, episode_id, seq, title, location, time_of_day, characters, action_text, dialogue, mood, duration_seconds, created_at) VALUES (2, 1, 1, 2, '灯塔控制台', '地下机房', '夜', '林澈、苏眠', '两人下到机房，能源读数一路下降，灯塔主控的光脉冲越来越慢。', '苏眠：能源只剩 12%，撑不到日出。
林澈：如果我能和它对话呢？', '紧张、期待', 32.0, '2026-11-21 17:09:47.355424');
INSERT INTO script_scenes (id, script_id, episode_id, seq, title, location, time_of_day, characters, action_text, dialogue, mood, duration_seconds, created_at) VALUES (3, 1, 1, 3, '最后一束光', '星海之门', '黎明前', '林澈、苏眠、观测者', '林澈把手放上光核，整座灯塔亮起，观测者的剪影浮现在星海之上。', '观测者：你终于想起来了。
林澈：这一次，我不会再走。', '震撼、治愈', 30.0, '2026-11-21 17:09:47.355424');

-- characters：3 行
INSERT INTO characters (id, series_id, name, role_type, personality, appearance_prompt, prompt_prefix, ref_asset_id, lora_name, lora_weight, seed, voice, created_at) VALUES (1, 1, '林澈', '主角', '安静、倔强，失去记忆却对星海异常熟悉。', 'silver short hair, amber eyes, white academy jacket, red scarf', 'girl with silver hair and amber eyes, anime cel shading', NULL, 'lin_che_v1', 0.85, 20240501, '少女音 / 清澈', '2026-11-21 17:09:47.349419');
INSERT INTO characters (id, series_id, name, role_type, personality, appearance_prompt, prompt_prefix, ref_asset_id, lora_name, lora_weight, seed, voice, created_at) VALUES (2, 1, '苏眠', '配角', '谨慎、可靠，值班十年的观测员。', 'dark green hair tied back, round glasses, worn orange maintenance uniform', 'young man with green hair and glasses, maintenance uniform, anime style', NULL, 'su_mian_v1', 0.75, 20240502, '青年音 / 温和', '2026-11-21 17:09:47.349419');
INSERT INTO characters (id, series_id, name, role_type, personality, appearance_prompt, prompt_prefix, ref_asset_id, lora_name, lora_weight, seed, voice, created_at) VALUES (3, 1, '观测者', '反派', '声音化的存在，代表灯塔的旧规则。', 'glowing silhouette, monolith figure, star fragment halo', 'mysterious glowing silhouette, halo of star fragments, void background', NULL, '', 0.8, 20240503, '混响低音', '2026-11-21 17:09:47.351422');

-- scene_cards：3 行
INSERT INTO scene_cards (id, series_id, name, description, atmosphere, prompt, prompt_prefix, ref_asset_id, seed, created_at) VALUES (1, 1, '废弃观测站', '锈迹斑斑的圆顶观测站，全息屏仍在闪烁。', '冷蓝夜色 + 红色警报灯', 'abandoned observatory interior, cracked dome, flickering hologram, dust in light beam', '', NULL, 1101, '2026-11-21 17:09:47.360423');
INSERT INTO scene_cards (id, series_id, name, description, atmosphere, prompt, prompt_prefix, ref_asset_id, seed, created_at) VALUES (2, 1, '地下机房', '管线密布的机房，能源读数一路下降。', '橙红应急灯 + 冷蓝数据光', 'underground machine room, tangled cables, emergency light, energy meter glow', '', NULL, 1102, '2026-11-21 17:09:47.360423');
INSERT INTO scene_cards (id, series_id, name, description, atmosphere, prompt, prompt_prefix, ref_asset_id, seed, created_at) VALUES (3, 1, '星海之门', '灯塔顶端，星海在脚下流动。', '深蓝星海 + 金色光核', 'lighthouse top open to a flowing star sea, golden light core, epic wide shot', '', NULL, 1103, '2026-11-21 17:09:47.360423');

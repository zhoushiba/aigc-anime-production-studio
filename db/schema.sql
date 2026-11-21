-- AI ModelOps / AIGC 动漫番剧制作工作台 —— 数据库结构（由 scripts/export_db.py 自动导出）
-- 数据库：SQLite（默认）。切换到 PostgreSQL/MySQL 时可直接参考本文件的表与约束定义。
CREATE TABLE asset_ratings (
	id INTEGER NOT NULL, 
	asset_id INTEGER NOT NULL, 
	user_id INTEGER, 
	score INTEGER NOT NULL, 
	comment VARCHAR(200) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(asset_id) REFERENCES assets (id)
);

CREATE TABLE asset_revisions (
	id INTEGER NOT NULL, 
	asset_id INTEGER NOT NULL, 
	new_asset_id INTEGER, 
	issues_json JSON NOT NULL, 
	fix_prompt TEXT NOT NULL, 
	task_id INTEGER, 
	note VARCHAR(200) NOT NULL, 
	created_by VARCHAR(50) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(asset_id) REFERENCES assets (id)
);

CREATE TABLE assets (
	id INTEGER NOT NULL, 
	series_id INTEGER, 
	episode_id INTEGER, 
	shot_id INTEGER, 
	character_id INTEGER, 
	scene_card_id INTEGER, 
	task_id INTEGER, 
	kind VARCHAR(20) NOT NULL, 
	title VARCHAR(120) NOT NULL, 
	file_path VARCHAR(255) NOT NULL, 
	thumb_path VARCHAR(255) NOT NULL, 
	width INTEGER NOT NULL, 
	height INTEGER NOT NULL, 
	file_size INTEGER NOT NULL, 
	seed INTEGER NOT NULL, 
	prompt TEXT NOT NULL, 
	negative_prompt TEXT NOT NULL, 
	provider VARCHAR(20) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	rating INTEGER NOT NULL, 
	review_note VARCHAR(200) NOT NULL, 
	meta_json JSON NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE characters (
	id INTEGER NOT NULL, 
	series_id INTEGER NOT NULL, 
	name VARCHAR(60) NOT NULL, 
	role_type VARCHAR(20) NOT NULL, 
	personality TEXT NOT NULL, 
	appearance_prompt TEXT NOT NULL, 
	prompt_prefix TEXT NOT NULL, 
	ref_asset_id INTEGER, 
	lora_name VARCHAR(80) NOT NULL, 
	lora_weight FLOAT NOT NULL, 
	seed INTEGER NOT NULL, 
	voice VARCHAR(60) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(series_id) REFERENCES series (id)
);

CREATE TABLE episodes (
	id INTEGER NOT NULL, 
	series_id INTEGER NOT NULL, 
	number INTEGER NOT NULL, 
	title VARCHAR(120) NOT NULL, 
	summary TEXT NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_episode_number UNIQUE (series_id, number), 
	FOREIGN KEY(series_id) REFERENCES series (id)
);

CREATE TABLE export_jobs (
	id INTEGER NOT NULL, 
	episode_id INTEGER NOT NULL, 
	timeline_id INTEGER, 
	format VARCHAR(10) NOT NULL, 
	file_path VARCHAR(255) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	payload_json JSON NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(episode_id) REFERENCES episodes (id)
);

CREATE TABLE generation_tasks (
	id INTEGER NOT NULL, 
	series_id INTEGER, 
	episode_id INTEGER, 
	shot_id INTEGER, 
	kind VARCHAR(20) NOT NULL, 
	provider VARCHAR(20) NOT NULL, 
	prompt TEXT NOT NULL, 
	negative_prompt TEXT NOT NULL, 
	params_json JSON NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	progress INTEGER NOT NULL, 
	error TEXT NOT NULL, 
	asset_id INTEGER, 
	seed INTEGER NOT NULL, 
	canceled BOOLEAN NOT NULL, 
	started_at DATETIME, 
	finished_at DATETIME, 
	duration_ms INTEGER NOT NULL, 
	created_by VARCHAR(50) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE prompt_history (
	id INTEGER NOT NULL, 
	series_id INTEGER, 
	shot_id INTEGER, 
	task_id INTEGER, 
	kind VARCHAR(20) NOT NULL, 
	prompt TEXT NOT NULL, 
	negative_prompt TEXT NOT NULL, 
	params_json JSON NOT NULL, 
	created_by VARCHAR(50) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE prompt_templates (
	id INTEGER NOT NULL, 
	name VARCHAR(80) NOT NULL, 
	category VARCHAR(20) NOT NULL, 
	style_key VARCHAR(40) NOT NULL, 
	content TEXT NOT NULL, 
	negative_prompt TEXT NOT NULL, 
	description VARCHAR(200) NOT NULL, 
	is_builtin BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE quality_checklists (
	id INTEGER NOT NULL, 
	episode_id INTEGER NOT NULL, 
	item_key VARCHAR(50) NOT NULL, 
	label VARCHAR(120) NOT NULL, 
	checked BOOLEAN NOT NULL, 
	note VARCHAR(200) NOT NULL, 
	checked_by VARCHAR(50) NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_checklist_item UNIQUE (episode_id, item_key), 
	FOREIGN KEY(episode_id) REFERENCES episodes (id)
);

CREATE TABLE reviews (
	id INTEGER NOT NULL, 
	series_id INTEGER, 
	target_type VARCHAR(20) NOT NULL, 
	target_id INTEGER NOT NULL, 
	title VARCHAR(160) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	comment TEXT NOT NULL, 
	submitted_by VARCHAR(50) NOT NULL, 
	reviewer_id INTEGER, 
	reviewer_name VARCHAR(50) NOT NULL, 
	created_at DATETIME NOT NULL, 
	decided_at DATETIME, 
	PRIMARY KEY (id)
);

CREATE TABLE scene_cards (
	id INTEGER NOT NULL, 
	series_id INTEGER NOT NULL, 
	name VARCHAR(60) NOT NULL, 
	description TEXT NOT NULL, 
	atmosphere VARCHAR(120) NOT NULL, 
	prompt TEXT NOT NULL, 
	prompt_prefix TEXT NOT NULL, 
	ref_asset_id INTEGER, 
	seed INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(series_id) REFERENCES series (id)
);

CREATE TABLE script_scenes (
	id INTEGER NOT NULL, 
	script_id INTEGER NOT NULL, 
	episode_id INTEGER NOT NULL, 
	seq INTEGER NOT NULL, 
	title VARCHAR(120) NOT NULL, 
	location VARCHAR(120) NOT NULL, 
	time_of_day VARCHAR(30) NOT NULL, 
	characters VARCHAR(200) NOT NULL, 
	action_text TEXT NOT NULL, 
	dialogue TEXT NOT NULL, 
	mood VARCHAR(60) NOT NULL, 
	duration_seconds FLOAT NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(script_id) REFERENCES scripts (id), 
	FOREIGN KEY(episode_id) REFERENCES episodes (id)
);

CREATE TABLE scripts (
	id INTEGER NOT NULL, 
	episode_id INTEGER NOT NULL, 
	version INTEGER NOT NULL, 
	structure VARCHAR(20) NOT NULL, 
	content TEXT NOT NULL, 
	is_current BOOLEAN NOT NULL, 
	created_by VARCHAR(50) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_script_version UNIQUE (episode_id, version), 
	FOREIGN KEY(episode_id) REFERENCES episodes (id)
);

CREATE TABLE series (
	id INTEGER NOT NULL, 
	title VARCHAR(120) NOT NULL, 
	genre VARCHAR(30) NOT NULL, 
	logline VARCHAR(300) NOT NULL, 
	synopsis TEXT NOT NULL, 
	episodes_planned INTEGER NOT NULL, 
	target_duration INTEGER NOT NULL, 
	style VARCHAR(60) NOT NULL, 
	platform VARCHAR(20) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	cover_prompt TEXT NOT NULL, 
	cover_asset_id INTEGER, 
	owner_id INTEGER, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(owner_id) REFERENCES users (id)
);

CREATE TABLE storyboard_shots (
	id INTEGER NOT NULL, 
	episode_id INTEGER NOT NULL, 
	seq INTEGER NOT NULL, 
	shot_no VARCHAR(20) NOT NULL, 
	shot_size VARCHAR(10) NOT NULL, 
	camera_angle VARCHAR(10) NOT NULL, 
	camera_move VARCHAR(10) NOT NULL, 
	duration_seconds FLOAT NOT NULL, 
	description TEXT NOT NULL, 
	dialogue TEXT NOT NULL, 
	bgm VARCHAR(120) NOT NULL, 
	characters VARCHAR(200) NOT NULL, 
	character_id INTEGER, 
	scene_card_id INTEGER, 
	prompt TEXT NOT NULL, 
	negative_prompt TEXT NOT NULL, 
	asset_id INTEGER, 
	status VARCHAR(20) NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(episode_id) REFERENCES episodes (id), 
	FOREIGN KEY(character_id) REFERENCES characters (id), 
	FOREIGN KEY(scene_card_id) REFERENCES scene_cards (id)
);

CREATE TABLE timeline_items (
	id INTEGER NOT NULL, 
	timeline_id INTEGER NOT NULL, 
	shot_id INTEGER, 
	asset_id INTEGER, 
	seq INTEGER NOT NULL, 
	duration_seconds FLOAT NOT NULL, 
	subtitle TEXT NOT NULL, 
	transition VARCHAR(20) NOT NULL, 
	audio_note VARCHAR(120) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(timeline_id) REFERENCES timelines (id)
);

CREATE TABLE timelines (
	id INTEGER NOT NULL, 
	episode_id INTEGER NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	total_duration FLOAT NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(episode_id) REFERENCES episodes (id)
);

CREATE TABLE users (
	id INTEGER NOT NULL, 
	username VARCHAR(50) NOT NULL, 
	password_hash VARCHAR(200) NOT NULL, 
	display_name VARCHAR(50) NOT NULL, 
	role VARCHAR(20) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX ix_asset_ratings_asset_id ON asset_ratings (asset_id);

CREATE INDEX ix_asset_revisions_asset_id ON asset_revisions (asset_id);

CREATE INDEX ix_assets_character_id ON assets (character_id);

CREATE INDEX ix_assets_created_at ON assets (created_at);

CREATE INDEX ix_assets_episode_id ON assets (episode_id);

CREATE INDEX ix_assets_series_id ON assets (series_id);

CREATE INDEX ix_assets_shot_id ON assets (shot_id);

CREATE INDEX ix_assets_status ON assets (status);

CREATE INDEX ix_assets_task_id ON assets (task_id);

CREATE INDEX ix_characters_series_id ON characters (series_id);

CREATE INDEX ix_episodes_series_id ON episodes (series_id);

CREATE INDEX ix_episodes_status ON episodes (status);

CREATE INDEX ix_export_jobs_episode_id ON export_jobs (episode_id);

CREATE INDEX ix_generation_tasks_created_at ON generation_tasks (created_at);

CREATE INDEX ix_generation_tasks_episode_id ON generation_tasks (episode_id);

CREATE INDEX ix_generation_tasks_series_id ON generation_tasks (series_id);

CREATE INDEX ix_generation_tasks_shot_id ON generation_tasks (shot_id);

CREATE INDEX ix_generation_tasks_status ON generation_tasks (status);

CREATE INDEX ix_prompt_history_series_id ON prompt_history (series_id);

CREATE INDEX ix_prompt_history_shot_id ON prompt_history (shot_id);

CREATE INDEX ix_quality_checklists_episode_id ON quality_checklists (episode_id);

CREATE INDEX ix_reviews_series_id ON reviews (series_id);

CREATE INDEX ix_reviews_status ON reviews (status);

CREATE INDEX ix_scene_cards_series_id ON scene_cards (series_id);

CREATE INDEX ix_script_scenes_episode_id ON script_scenes (episode_id);

CREATE INDEX ix_script_scenes_script_id ON script_scenes (script_id);

CREATE INDEX ix_scripts_episode_id ON scripts (episode_id);

CREATE INDEX ix_series_status ON series (status);

CREATE INDEX ix_series_title ON series (title);

CREATE INDEX ix_shots_episode_seq ON storyboard_shots (episode_id, seq);

CREATE INDEX ix_storyboard_shots_episode_id ON storyboard_shots (episode_id);

CREATE INDEX ix_storyboard_shots_status ON storyboard_shots (status);

CREATE INDEX ix_timeline_items_seq ON timeline_items (timeline_id, seq);

CREATE INDEX ix_timeline_items_timeline_id ON timeline_items (timeline_id);

CREATE UNIQUE INDEX ix_timelines_episode_id ON timelines (episode_id);

CREATE INDEX ix_users_role ON users (role);

CREATE UNIQUE INDEX ix_users_username ON users (username);

"""种子数据：让项目「打开即有完整工作流」。

一个示例剧集《星海拾光》：
- 3 集、第 1 集 3 场戏 + 8 个分镜（带提示词与两张已生成素材）
- 3 张角色设定卡、3 张场景卡、12 套内置画风模板
- 成片合成单、质检清单、待审核单
- 4 个不同角色的演示账号
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.constants import (
    ASSET_STATUS_LABELS,  # noqa: F401
    QUALITY_ITEMS,
    STYLE_PRESETS,
)
from app.database import session_scope
from app.models import (
    Asset,
    Character,
    Episode,
    PromptTemplate,
    QualityChecklist,
    Review,
    SceneCard,
    Script,
    ScriptScene,
    Series,
    StoryboardShot,
    Timeline,
    TimelineItem,
    User,
    utcnow,
)
from app.security import hash_password
from app.services.image_utils import save_asset_image
from app.services.providers import GenerationRequest, get_provider

logger = logging.getLogger("app.seed")

DEMO_USERS = [
    ("director", "林导", "director"),
    ("storyboard", "苏分镜", "storyboard"),
    ("artist", "阿美术", "artist"),
    ("reviewer", "王审核", "reviewer"),
    ("student", "小学员", "student"),
]


def _style_choices() -> list[dict[str, str]]:
    """把 constants.STYLE_PRESETS 归一化成模板字段（style_key/content/negative_prompt/description）。"""
    from app.services.prompt_builder import _normalize_style

    raw = STYLE_PRESETS
    items: list[dict[str, str]] = []
    if isinstance(raw, dict):
        raw = [{"style_key": key, **(value if isinstance(value, dict) else {"content": str(value)})} for key, value in raw.items()]
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        normalized = _normalize_style(item)
        items.append(
            {
                "key": normalized["key"],
                "name": normalized["name"],
                "prompt": normalized["prompt"],
                "negative": normalized["negative"],
                "description": str(item.get("description") or ""),
            }
        )
    return items


def seed_users(db: Session) -> dict[str, User]:
    users: dict[str, User] = {}
    for username, display_name, role in DEMO_USERS:
        user = db.scalar(select(User).where(User.username == username))
        if user is None:
            user = User(
                username=username,
                password_hash=hash_password(settings.demo_password),
                display_name=display_name,
                role=role,
            )
            db.add(user)
            db.flush()
        users[username] = user
    return users


def seed_prompt_templates(db: Session) -> int:
    if db.scalar(select(PromptTemplate).limit(1)) is not None:
        return 0
    created = 0
    for item in _style_choices():
        db.add(
            PromptTemplate(
                name=item["name"] or item["key"],
                category="style",
                style_key=item["key"],
                content=item["prompt"],
                negative_prompt=item["negative"],
                description=item["description"] or f"{item['name']} 画风预设",
                is_builtin=True,
            )
        )
        created += 1
    return created


def seed_series(db: Session, users: dict[str, User]) -> Series | None:
    if db.scalar(select(Series).limit(1)) is not None:
        return None
    series = Series(
        title="星海拾光",
        genre="科幻 / 治愈",
        logline="失去记忆的少女与观测员，在星海灯塔上收集散落的光。",
        synopsis=(
            "第 1 集《灯塔亮起》：少女林澈在废弃观测站醒来，失去了过往记忆。"
            "值班观测员苏眠发现她能与星海 Lighthouse 系统共鸣，"
            "两人决定重启灯塔，为即将熄灭的星海补上最后一束光。"
        ),
        episodes_planned=6,
        target_duration=90,
        style="日系赛璐璐",
        platform="vertical",
        status="in_production",
        cover_prompt="star sea lighthouse, girl and observer silhouette, cel shading anime style",
        owner_id=users["director"].id,
    )
    db.add(series)
    db.flush()

    episodes = [
        Episode(series_id=series.id, number=1, title="灯塔亮起", summary="林澈醒来，与苏眠相遇。", status="storyboard"),
        Episode(series_id=series.id, number=2, title="失重的回音", summary="星海出现异常回波。", status="scripting"),
        Episode(series_id=series.id, number=3, title="最后一束光", summary="灯塔重启，代价浮现。", status="draft"),
    ]
    db.add_all(episodes)
    db.flush()
    episode = episodes[0]

    script = Script(
        episode_id=episode.id,
        version=1,
        structure="三幕式",
        is_current=True,
        created_by=users["director"].username,
        content=(
            "第一幕 · 建置\n"
            "夜。废弃观测站。林澈从通讯台前醒来，全息屏幕还亮着上一段留言。\n\n"
            "第二幕 · 对抗\n"
            "苏眠发现灯塔能源只剩 12%，两人尝试用星海回波补能。\n\n"
            "第三幕 · 收束\n"
            "灯塔亮起，林澈的记忆碎片浮现，画面推向星海。"
        ),
    )
    db.add(script)
    db.flush()

    db.add_all(
        [
            ScriptScene(
                script_id=script.id,
                episode_id=episode.id,
                seq=1,
                title="观测站初醒",
                location="废弃观测站",
                time_of_day="深夜",
                characters="林澈、苏眠",
                action_text="林澈睁眼，红色的警报灯在墙面上扫过。苏眠推门进来，手里提着应急灯。",
                dialogue="苏眠：你醒了？这台通讯机三年没响过了。\n林澈：我……记不起自己的名字。",
                mood="悬疑、疏离",
                duration_seconds=28,
            ),
            ScriptScene(
                script_id=script.id,
                episode_id=episode.id,
                seq=2,
                title="灯塔控制台",
                location="地下机房",
                time_of_day="夜",
                characters="林澈、苏眠",
                action_text="两人下到机房，能源读数一路下降，灯塔主控的光脉冲越来越慢。",
                dialogue="苏眠：能源只剩 12%，撑不到日出。\n林澈：如果我能和它对话呢？",
                mood="紧张、期待",
                duration_seconds=32,
            ),
            ScriptScene(
                script_id=script.id,
                episode_id=episode.id,
                seq=3,
                title="最后一束光",
                location="星海之门",
                time_of_day="黎明前",
                characters="林澈、苏眠、观测者",
                action_text="林澈把手放上光核，整座灯塔亮起，观测者的剪影浮现在星海之上。",
                dialogue="观测者：你终于想起来了。\n林澈：这一次，我不会再走。",
                mood="震撼、治愈",
                duration_seconds=30,
            ),
        ]
    )

    characters = [
        Character(
            series_id=series.id,
            name="林澈",
            role_type="主角",
            personality="安静、倔强，失去记忆却对星海异常熟悉。",
            appearance_prompt="silver short hair, amber eyes, white academy jacket, red scarf",
            prompt_prefix="girl with silver hair and amber eyes, anime cel shading",
            lora_name="lin_che_v1",
            lora_weight=0.85,
            seed=20240501,
            voice="少女音 / 清澈",
        ),
        Character(
            series_id=series.id,
            name="苏眠",
            role_type="配角",
            personality="谨慎、可靠，值班十年的观测员。",
            appearance_prompt="dark green hair tied back, round glasses, worn orange maintenance uniform",
            prompt_prefix="young man with green hair and glasses, maintenance uniform, anime style",
            lora_name="su_mian_v1",
            lora_weight=0.75,
            seed=20240502,
            voice="青年音 / 温和",
        ),
        Character(
            series_id=series.id,
            name="观测者",
            role_type="反派",
            personality="声音化的存在，代表灯塔的旧规则。",
            appearance_prompt="glowing silhouette, monolith figure, star fragment halo",
            prompt_prefix="mysterious glowing silhouette, halo of star fragments, void background",
            seed=20240503,
            voice="混响低音",
        ),
    ]
    db.add_all(characters)
    db.flush()

    scenes = [
        SceneCard(
            series_id=series.id,
            name="废弃观测站",
            description="锈迹斑斑的圆顶观测站，全息屏仍在闪烁。",
            atmosphere="冷蓝夜色 + 红色警报灯",
            prompt="abandoned observatory interior, cracked dome, flickering hologram, dust in light beam",
            seed=1101,
        ),
        SceneCard(
            series_id=series.id,
            name="地下机房",
            description="管线密布的机房，能源读数一路下降。",
            atmosphere="橙红应急灯 + 冷蓝数据光",
            prompt="underground machine room, tangled cables, emergency light, energy meter glow",
            seed=1102,
        ),
        SceneCard(
            series_id=series.id,
            name="星海之门",
            description="灯塔顶端，星海在脚下流动。",
            atmosphere="深蓝星海 + 金色光核",
            prompt="lighthouse top open to a flowing star sea, golden light core, epic wide shot",
            seed=1103,
        ),
    ]
    db.add_all(scenes)
    db.flush()

    shot_specs = [
        ("01", "远景", "俯视", "固定", 6.0, "废弃观测站外景，暴风雪中的圆顶亮着一盏灯。", "", "低音弦乐", "林澈", 0, 0, 0),
        ("02", "中景", "平视", "推", 5.0, "林澈从控制台前醒来，红色警报灯扫过脸颊。", "苏眠：你醒了？", "心跳声", "林澈、苏眠", 0, 0, 1),
        ("03", "近景", "斜视", "固定", 4.0, "苏眠提着应急灯走近，镜片反射光斑。", "苏眠：这台通讯机三年没响过了。", "脚步回声", "苏眠", 1, 0, 1),
        ("04", "全景", "俯视", "移", 5.5, "两人下到机房，管线与能源读数占满画面。", "", "机械低鸣", "林澈、苏眠", 1, 1, 2),
        ("05", "特写", "平视", "固定", 3.5, "能源读数只剩 12%，数字闪烁。", "林澈：如果我能和它对话呢？", "电子蜂鸣", "林澈", 0, 1, 2),
        ("06", "中景", "仰视", "升降", 6.0, "林澈把手放上光核，光脉冲向外扩散。", "苏眠：撑不到日出！", "弦乐渐强", "林澈、苏眠", 0, 2, 3),
        ("07", "远景", "平视", "推", 7.0, "灯塔亮起，光柱穿透星海，观测者剪影浮现。", "观测者：你终于想起来了。", "合唱人声", "观测者", 2, 2, 4),
        ("08", "特写", "平视", "固定", 4.0, "林澈的眼睛里映出星海，泪光闪烁。", "林澈：这一次，我不会再走。", "钢琴单音", "林澈", 0, 2, 4),
    ]
    shots: list[StoryboardShot] = []
    for seq, (shot_no, size, angle, move, duration, desc, dialogue, bgm, chars, char_idx, scene_idx, _seed) in enumerate(
        shot_specs, start=1
    ):
        character = characters[char_idx]
        scene = scenes[min(scene_idx, len(scenes) - 1)]
        shots.append(
            StoryboardShot(
                episode_id=episode.id,
                seq=seq,
                shot_no=shot_no,
                shot_size=size,
                camera_angle=angle,
                camera_move=move,
                duration_seconds=duration,
                description=desc,
                dialogue=dialogue,
                bgm=bgm,
                characters=chars,
                character_id=character.id,
                scene_card_id=scene.id,
                prompt=(
                    f"{desc}, {size} {angle} {move}, {scene.prompt}, "
                    f"{character.prompt_prefix}, cel shading anime style, cinematic lighting"
                ),
                negative_prompt="lowres, blurry, extra limbs, bad hands, text, watermark",
                status="prompted",
            )
        )
    db.add_all(shots)
    db.flush()

    # 用 MockProvider 真实渲染两张素材，让素材库/看板一打开就有内容
    provider = get_provider("mock")
    today = utcnow().strftime("%Y%m%d")
    settings.ensure_dirs()
    for index, shot in enumerate(shots[:2]):
        try:
            result = provider.generate(
                GenerationRequest(
                    prompt=shot.prompt,
                    negative_prompt=shot.negative_prompt,
                    seed=900 + index,
                    size=settings.vertical_size,
                    params={"steps": 24, "cfg_scale": 7.0},
                    shot_label=f"{shot.shot_no} {shot.shot_size}",
                    style_label=series.style,
                )
            )
            saved = save_asset_image(
                result.image,
                directory=settings.assets_dir / today,
                thumbs_dir=settings.thumbs_dir,
                stem=f"seed{index}",
                thumb_width=settings.thumb_width,
            )
            asset = Asset(
                series_id=series.id,
                episode_id=episode.id,
                shot_id=shot.id,
                character_id=shot.character_id,
                kind="image",
                title=f"镜 {shot.shot_no} · {shot.shot_size}",
                file_path=saved["path"].relative_to(settings.storage_dir).as_posix(),
                thumb_path=saved["thumb_path"].relative_to(settings.storage_dir).as_posix(),
                width=int(saved["width"]),
                height=int(saved["height"]),
                file_size=int(saved["file_size"]),
                seed=900 + index,
                prompt=shot.prompt,
                negative_prompt=shot.negative_prompt,
                provider="mock",
                status="selected" if index == 0 else "candidate",
                rating=5 if index == 0 else 4,
                meta_json={**result.meta, "seed_asset": True},
            )
            db.add(asset)
            db.flush()
            shot.asset_id = asset.id
            shot.status = "generated"
            if index == 0:
                series.cover_asset_id = asset.id
        except Exception:  # pragma: no cover - 仅影响种子观感
            logger.exception("种子素材生成失败")

    timeline = Timeline(episode_id=episode.id, name="第 1 集 · 成片合成单", status="draft")
    db.add(timeline)
    db.flush()
    total = 0.0
    for seq, shot in enumerate(shots, start=1):
        total += float(shot.duration_seconds)
        db.add(
            TimelineItem(
                timeline_id=timeline.id,
                shot_id=shot.id,
                asset_id=shot.asset_id,
                seq=seq,
                duration_seconds=shot.duration_seconds,
                subtitle=shot.dialogue,
                transition="dissolve" if seq in (3, 6) else "cut",
                audio_note=shot.bgm,
            )
        )
    timeline.total_duration = round(total, 2)

    for item in QUALITY_ITEMS:
        if isinstance(item, dict):
            key = str(item.get("key") or item.get("item_key") or "")
            label = str(item.get("label") or key)
        else:
            key, label = str(item), str(item)
        if not key:
            continue
        db.add(QualityChecklist(episode_id=episode.id, item_key=key, label=label, checked=False))

    db.add(
        Review(
            series_id=series.id,
            target_type="episode",
            target_id=episode.id,
            title="第 1 集 分镜与素材提交审核",
            status="pending",
            comment="分镜 8 个镜头已完成 2 张素材，请审核画面一致性。",
            submitted_by=users["storyboard"].username,
        )
    )
    logger.info("种子数据：剧集《%s》，%s 个分镜", series.title, len(shots))
    return series


def seed_all() -> dict:
    """幂等种子；返回概要供 /health 展示。"""
    with session_scope() as db:
        users = seed_users(db)
        templates = seed_prompt_templates(db)
        series = seed_series(db, users)
        summary = {
            "users": len(users),
            "prompt_templates": templates,
            "series_created": bool(series),
        }
    logger.info("种子数据完成：%s", summary)
    return summary

from pydantic import BaseModel, Field


class GelbooruPost(BaseModel):
    id: int
    width: int
    height: int
    directory: str
    image: str
    rating: str
    source: str
    change: int
    owner: str
    parent_id: int
    tags: str
    has_notes: bool
    file_url: str
    preview_url: str
    sample_url: str
    sample_height: int
    sample_width: int
    status: str
    score: int | None = None
    sample: int | bool | None = None
    preview_height: int | None = None
    preview_width: int | None = None
    title: str | None = None
    has_comments: bool | None = None
    comment_count: int | None = None
    post_locked: int | None = None
    has_children: bool | None = None
    creator_id: int | None = None
    md5: str | None = None
    hash: str | None = None
    created_at: str | None = None


class GelbooruSearchResponse(BaseModel):
    attributes: dict = Field(default_factory=dict, alias="@attributes")
    post: list[GelbooruPost] = Field(default_factory=list)


class DanbooruMediaVariant(BaseModel):
    type: str
    url: str
    width: int
    height: int
    file_ext: str


class DanbooruMediaAsset(BaseModel):
    id: int
    created_at: str
    updated_at: str
    file_ext: str
    file_size: int
    image_width: int
    image_height: int
    duration: int | None
    status: str
    is_public: bool
    pixel_hash: str
    file_key: str | None = None
    variants: list[DanbooruMediaVariant] | None = None
    md5: str | None = None


class DanbooruPost(BaseModel):
    id: int
    created_at: str
    uploader_id: int
    score: int
    source: str
    last_comment_bumped_at: str | None
    rating: str
    image_width: int
    image_height: int
    tag_string: str
    fav_count: int
    file_ext: str
    last_noted_at: str | None
    parent_id: int | None
    has_children: bool
    approver_id: int | None
    tag_count_general: int
    tag_count_artist: int
    tag_count_character: int
    tag_count_copyright: int
    file_size: int
    up_score: int
    down_score: int
    is_pending: bool
    is_flagged: bool
    is_deleted: bool
    tag_count: int
    updated_at: str
    is_banned: str
    pixiv_id: int | None
    last_commented_at: str | None
    has_active_children: bool
    bit_flags: int
    tag_count_meta: int
    has_large: bool
    has_visible_children: bool
    media_asset: DanbooruMediaAsset
    tag_string_general: str
    tag_string_character: str
    tag_string_copyright: str
    tag_string_artist: str
    tag_string_meta: str
    md5: str | None = None
    file_url: str | None = None
    large_file_url: str | None = None
    preview_file_url: str | None = None

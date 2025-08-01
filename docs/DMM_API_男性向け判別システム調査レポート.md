# DMM API 男性向け作品判別システム調査レポート

## 📋 概要

本レポートは、DMM APIの各エンドポイントを調査し、男性向け作品の判別に使用できる情報を分析したものです。現在のシステムで使用している機能と、改善可能な機能について詳細に記載します。

## 🎯 調査対象APIエンドポイント

1. **FloorList API** - フロア一覧（カテゴリ階層）
2. **ItemList API** - 商品一覧（現在メインで使用中）
3. **GenreSearch API** - ジャンル検索
4. **SeriesSearch API** - シリーズ検索
5. **AuthorSearch API** - 作者検索

---

## 1. 現在のシステムでの使用状況

### 1.1 使用中のAPIパラメータ

現在のシステム（`src/api/dmm_api.py`）では以下のパラメータを使用：

```python
params = {
    'api_id': self.api_id,
    'affiliate_id': self.affiliate_id,
    'site': 'FANZA',                 # FANZAサイト（アダルト向け）
    'service': 'doujin',             # 同人サービス
    'floor': 'digital_doujin',       # 同人フロア（floor_id: 81）
    'hits': limit,
    'offset': offset,
    'sort': 'date',                  # 新着順
    'output': 'json'
}
```

### 1.2 男性向け作品判別ロジック

現在のシステムでは複数の判定基準を組み合わせて男性向け作品を識別：

#### 📂 画像URLによる判定
```python
if '/digital/comic/' in image_url:
    return self._is_male_oriented_work(api_item)
```

#### 🏷️ ジャンルによる判定
```python
# 女性向けジャンルの除外
female_oriented_genres = [
    '女性向け', 'BL', 'ボーイズラブ', '乙女',
    'TL', 'ティーンズラブ', '少女マンガ',
    '恋愛', 'ラブロマンス', '少女向け'
]

# 男性向けジャンルの確認
male_oriented_genres = [
    '男性向け', '成人向け', 'アダルト', 'エロ',
    '青年向け', '大人向け', 'R18', '18禁'
]
```

---

## 2. DMM API エンドポイント詳細調査

### 2.1 FloorList API（フロア一覧）

**エンドポイント**: `https://api.dmm.com/affiliate/v3/FloorList`

**主要機能**:
- サイト・サービス・フロアの階層構造を取得
- 利用可能なカテゴリの全体像を把握

**男性向け作品判別への活用**:
- ✅ `site: FANZA`でアダルト向けコンテンツを識別
- ✅ `floor_id: 81 (digital_doujin)`で同人作品を特定

**利用可能パラメータ**:
```json
{
    "api_id": "必須",
    "affiliate_id": "必須", 
    "output": "json|xml"
}
```

### 2.2 ItemList API（商品一覧）⭐️ 現在メイン使用中

**エンドポイント**: `https://api.dmm.com/affiliate/v3/ItemList`

**現在の活用状況**: ★★★★★（フル活用中）

**男性向け作品判別への有効性**:
- ✅ `site=FANZA`により成人向けコンテンツに限定
- ✅ `service=doujin`で同人作品に絞り込み
- ✅ `floor=digital_doujin`でデジタル同人に特化
- ✅ レスポンス内の`iteminfo.genre`で詳細ジャンル判定

**改善可能なパラメータ**:
```python
# 現在未使用だが活用可能
params = {
    'article': 'genre',              # ジャンルフィルタ
    'article_id': '特定ジャンルID',    # 具体的なジャンル指定
    'keyword': '検索キーワード',       # キーワード検索
    'gte_date': '2024-01-01',        # 期間指定
}
```

### 2.3 GenreSearch API（ジャンル検索）🆕 活用推奨

**エンドポイント**: `https://api.dmm.com/affiliate/v3/GenreSearch`

**現在の活用状況**: ★☆☆☆☆（未使用）

**男性向け作品判別への潜在的活用**:
- 📊 事前にジャンルIDとジャンル名のマッピングを取得
- 🎯 男性向け・女性向けジャンルの体系的把握
- 🔍 ItemList APIでの`article_id`パラメータに活用

**利用可能パラメータ**:
```json
{
    "api_id": "必須",
    "affiliate_id": "必須",
    "floor_id": "81",  // digital_doujin
    "initial": "あ",   // 50音検索
    "hits": 500,       // 最大500件
    "output": "json"
}
```

**レスポンス例**:
```json
{
    "result": {
        "genre": [
            {
                "genre_id": "12345",
                "name": "男性向け",
                "ruby": "だんせいむけ",
                "list_url": "..."
            }
        ]
    }
}
```

### 2.4 SeriesSearch API（シリーズ検索）

**エンドポイント**: `https://api.dmm.com/affiliate/v3/SeriesSearch`

**現在の活用状況**: ★☆☆☆☆（未使用）

**男性向け作品判別への活用可能性**:
- 📚 シリーズ単位での作品傾向把握
- 🏆 人気シリーズによる男性向け作品の特定

**制限事項**:
- ⚠️ 同人作品に特化したシリーズ検索の詳細情報は限定的
- ⚠️ 主に商業作品向けの機能

### 2.5 AuthorSearch API（作者検索）

**エンドポイント**: `https://api.dmm.com/affiliate/v3/AuthorSearch`

**現在の活用状況**: ★☆☆☆☆（未使用）

**男性向け作品判別への活用可能性**:
- 👥 作者・サークル単位での作品傾向分析
- 🎨 男性向け作品を多く手がける作者の特定

**利用可能パラメータ**:
```json
{
    "api_id": "必須",
    "affiliate_id": "必須", 
    "floor_id": "81",
    "initial": "作者名読み仮名",
    "hits": 500,
    "output": "json"
}
```

---

## 3. 男性向け作品判別の改善提案

### 3.1 現在のシステムの強み ✨

1. **複層的判定**: 画像URL、ジャンル、カテゴリ、タイトルを組み合わせた総合判定
2. **厳格フィルタリング**: コミック作品以外を明確に除外
3. **実装済み除外リスト**: 女性向けジャンルの包括的な除外パターン

### 3.2 改善可能な点 🔧

#### 3.2.1 GenreSearch APIの活用

**提案**: 事前にジャンル情報を取得して判定精度を向上

```python
def update_genre_mapping(self):
    """ジャンル情報を事前取得してマッピングテーブルを更新"""
    genre_response = self.session.get(
        f"{self.api_base_url}/GenreSearch",
        params={
            'api_id': self.api_id,
            'affiliate_id': self.affiliate_id,
            'floor_id': '81',  # digital_doujin
            'hits': 500,
            'output': 'json'
        }
    )
    
    # 男性向け・女性向けジャンルを体系的に分類
    male_genres = {}
    female_genres = {}
    # ... 実装詳細
```

#### 3.2.2 article/article_idパラメータの活用

**提案**: ItemList APIでより精密なフィルタリング

```python
# 男性向けジャンルに限定した検索
params.update({
    'article': 'genre',
    'article_id': '男性向けジャンルID'  # GenreSearch APIで取得
})
```

#### 3.2.3 キーワード検索の併用

```python
# ネガティブキーワードでの除外
params.update({
    'keyword': '-BL -女性向け -乙女'  # 除外キーワード
})
```

### 3.3 実装優先度

| 改善項目 | 優先度 | 実装コスト | 効果予想 |
|---------|-------|----------|---------|
| GenreSearch APIの活用 | 高 | 中 | 高 |
| article_idパラメータ活用 | 高 | 低 | 中 |
| AuthorSearch API活用 | 中 | 高 | 中 |
| キーワード検索活用 | 低 | 低 | 低 |

---

## 4. 現在未使用の有用機能

### 4.1 期間指定検索 📅

```python
params.update({
    'gte_date': '2024-01-01',  # 指定日以降
    'lte_date': '2024-12-31'   # 指定日以前
})
```

### 4.2 詳細ソート機能 🔄

```python
params.update({
    'sort': 'rank',      # 人気順
    'sort': 'price+',    # 価格昇順
    'sort': 'price-',    # 価格降順
    'sort': 'review'     # レビュー順
})
```

---

## 5. 結論と推奨事項

### 5.1 現在のシステム評価 📊

現在のシステムは**十分に効果的**で、複数の判定基準を組み合わせた堅実な実装になっています。

**特に優れている点**:
- ✅ 画像URLによる作品種別判定
- ✅ 包括的な女性向けジャンル除外
- ✅ 厳格なコミック作品フィルタリング

これらは男性向け作品判別において高い精度を実現しています。

### 5.2 短期改善推奨 🚀

1. **GenreSearch APIの活用**: ジャンル情報の事前取得による判定精度向上
2. **article_idパラメータの活用**: より精密な初期フィルタリング

### 5.3 長期改善検討 🔮

1. **AuthorSearch APIの活用**: 作者・サークル単位での傾向分析
2. **機械学習的アプローチ**: 過去の判定結果を学習データとした自動判別

### 5.4 APIによる男性向け判別の結論

**Q: APIで男性向けを判別することは難しいか？**

**A: 現在の実装で十分可能です。**

理由：
- DMM APIは`site=FANZA`で成人向けコンテンツに限定可能
- ジャンル情報が詳細に提供されている
- 現在のシステムは既に高精度で判別を実現

**追加改善の余地**：
- GenreSearch APIを活用すれば、より体系的な判別が可能
- ただし、現在の実装でも実用上十分な精度を達成

---

## 📝 付録：クイックリファレンス

### 現在使用中のAPI
- **ItemList API**: 商品一覧取得（メイン機能）

### 推奨追加API
- **GenreSearch API**: ジャンル体系の把握

### 判別キーワード
- **除外**: BL, 女性向け, 乙女, TL
- **採用**: 男性向け, 成人向け, アダルト, R18

### 重要パラメータ
- `site=FANZA`: 成人向けコンテンツ
- `service=doujin`: 同人作品
- `floor=digital_doujin`: デジタル同人
# Places Explorer - Visual Design Guide

## UI Layout

```
┌───────────────────────────────────────────────────────────────┐
│                    🗺️ Places Explorer                          │
│     Discover the best-rated destinations around the globe      │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  📍 seattle          [🔍 Search City]                   │  │
│  └─────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────┐
│  ⚡ Lightning Fast! Data loaded from cache for San Diego       │
└───────────────────────────────────────────────────────────────┘

┌═══════════════════════════════════════════════════════════════┐
║         👑 EXPERT'S CHOICE RECOMMENDATIONS                    ║
║         Top 10 highest-rated destinations                      ║
╠═══════════════════════════════════════════════════════════════╣
║                                                                ║
║  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌──────────┐║
║  │👑 Choice #1 │ │👑 Choice #2 │ │👑 Choice #3 │ │👑 Choice│║
║  │ [IMAGE]  4.8│ │ [IMAGE]  4.7│ │ [IMAGE]  4.6│ │ #4      │║
║  │             │ │             │ │             │ │ [IMAGE] │║
║  │Balboa Park  │ │Seaport      │ │SeaWorld     │ │Old Town │║
║  │👥 77,069    │ │Village      │ │San Diego    │ │         │║
║  │reviews      │ │👥 30,809    │ │👥 52,455    │ │👥 2,007 │║
║  │             │ │reviews      │ │reviews      │ │reviews  │║
║  │Visitors say │ │People say   │ │Ocean park   │ │Historic │║
║  │this park... │ │this is a... │ │featuring... │ │Mexican  │║
║  │⭐⭐⭐⭐⭐   │ │⭐⭐⭐⭐⭐   │ │⭐⭐⭐⭐☆   │ │quarter..│║
║  │[View Detail]│ │[View Detail]│ │[View Detail]│ │[View]   │║
║  └─────────────┘ └─────────────┘ └─────────────┘ └──────────┘║
║                                                                ║
║  ... 6 more expert choices ...                                ║
╚═══════════════════════════════════════════════════════════════╝

┌───────────────────────────────────────────────────────────────┐
│         📍 ALL DESTINATIONS                                    │
│         Explore 60 amazing places in San Diego                 │
├───────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌──────────┐│
│  │ [IMAGE]  4.8│ │ [IMAGE]  4.7│ │ [IMAGE]  4.6│ │ [IMAGE] ││
│  │             │ │             │ │             │ │         ││
│  │Place Name   │ │Place Name   │ │Place Name   │ │Place    ││
│  │👥 Reviews   │ │👥 Reviews   │ │👥 Reviews   │ │Name     ││
│  │Description..│ │Description..│ │Description..│ │👥       ││
│  │⭐⭐⭐⭐☆   │ │⭐⭐⭐⭐⭐   │ │⭐⭐⭐⭐☆   │ │Desc...  ││
│  │[View Detail]│ │[View Detail]│ │[View Detail]│ │[View]   ││
│  └─────────────┘ └─────────────┘ └─────────────┘ └──────────┘│
│                                                                │
│  ... all remaining places ...                                  │
└───────────────────────────────────────────────────────────────┘
```

## Card Design (Front)

```
┌──────────────────────────────────┐
│ 👑 Expert's Choice #1            │ ← Gold gradient badge
│ ┌────────────────────────────┐   │
│ │                            │   │
│ │      [PLACE IMAGE]         │   │
│ │                            │   │ ⭐ 4.8 ← White badge
│ │                            │   │        (top right)
│ └────────────────────────────┘   │
│                                   │
│ Balboa Park                       │ ← Name (bold, large)
│ 👥 77,069 reviews                 │ ← Review count
│                                   │
│ Visitors say this park offers     │ ← Description
│ stunning Spanish architecture,    │   (15 words max)
│ beautiful gardens... ...          │   ← "..." if longer
│                                   │
│ ⭐⭐⭐⭐⭐                        │ ← Visual stars
│                                   │
│ [park] [tourist attraction]       │ ← Type tags (max 2)
│                                   │
│ ┌─────────────────────────────┐  │
│ │ ℹ️ View Details             │  │ ← Action button
│ └─────────────────────────────┘  │
└──────────────────────────────────┘
```

## Modal Design (Click on Card)

```
╔════════════════════════════════════════════════╗
║  ┌──────────────────────────────────────────┐ ║
║  │                                          │ ║
║  │         [LARGE PLACE IMAGE]              │ ║  ❌ ← Close
║  │                                          │ ║
║  │  ┌───────────────────────────────────┐  │ ║
║  │  │ Balboa Park                       │  │ ║
║  │  │ ⭐ 4.8  (77,069 reviews)          │  │ ║
║  │  └───────────────────────────────────┘  │ ║
║  └──────────────────────────────────────────┘ ║
║                                                ║
║  ℹ️ About                                      ║
║  Visitors say this park offers stunning        ║
║  Spanish architecture, beautiful gardens       ║
║  including a rose garden and Japanese          ║
║  garden, and a variety of museums.             ║
║  (Full generativeSummary text - no truncation) ║
║                                                ║
║  💬 What People Say                            ║
║  ┌──────────────────────────────────────────┐ ║
║  │ They also highlight the peaceful and     │ ║
║  │ relaxing atmosphere, with many enjoying  │ ║
║  │ picnics, walks, and cultural events.     │ ║
║  │ (Full reviewSummary text)                │ ║
║  └──────────────────────────────────────────┘ ║
║     ↑ Styled box with gray background         ║
║                                                ║
║  🕐 Opening Hours                              ║
║  Monday: 10:00 AM – 5:00 PM                   ║
║  Tuesday: 10:00 AM – 5:00 PM                  ║
║  ... (all weekdays)                            ║
║                                                ║
║  ✅ Amenities                                  ║
║  [👶 Good for Children] [💳 Credit Cards]     ║
║  [📱 NFC Payments] [💵 Debit Cards]           ║
║                                                ║
║  ┌─────────────────┐  ┌──────────────────┐   ║
║  │ 🌐 Visit Website│  │ 📍 View in Map   │   ║
║  └─────────────────┘  └──────────────────┘   ║
╚════════════════════════════════════════════════╝
```

## Color Scheme

### Expert's Choice Badge
- Background: Linear gradient gold (#fbbf24 → #f59e0b)
- Text: Dark brown (#78350f)
- Shadow: Golden glow

### Rating Badge
- Background: White with transparency (rgba(255, 255, 255, 0.95))
- Backdrop: Blur effect
- Text: Dark gray (#111827)
- Star: Gold (#fbbf24)

### Expert Section
- Background tint: Light gold (rgba(251, 191, 36, 0.05))
- Border: Golden outline (rgba(251, 191, 36, 0.2))

### Review Summary Box
- Background: Light gray (#f9fafb)
- Border-left: Purple accent (#7c3aed, 4px)
- Text: Italic style

## Ranking System

Places are sorted by `rank_score` (highest first):

| Rank | Place | Score | Badge |
|------|-------|-------|-------|
| #1 | Balboa Park | 0.967 | 👑 Expert's Choice #1 |
| #2 | Seaport Village | 0.927 | 👑 Expert's Choice #2 |
| #3 | SeaWorld | 0.897 | 👑 Expert's Choice #3 |
| ... | ... | ... | ... |
| #10 | (10th place) | 0.XXX | 👑 Expert's Choice #10 |
| #11+ | Regular places | < 0.XXX | (no badge) |

## Text Truncation Logic

```
Original: "Visitors say this park offers stunning Spanish architecture, beautiful gardens including a rose garden and Japanese garden, and a variety of museums."

Word count: 24 words

Front card (15 words):
"Visitors say this park offers stunning Spanish architecture, beautiful gardens including a rose garden and..."

Modal (full text):
"Visitors say this park offers stunning Spanish architecture, beautiful gardens including a rose garden and Japanese garden, and a variety of museums."
```

## Responsive Breakpoints

- **Mobile (< 640px)**: 1 column
- **Tablet (640px - 1024px)**: 2 columns
- **Desktop (1024px - 1280px)**: 3 columns
- **Large Desktop (> 1280px)**: 4 columns

## Animation Effects

1. **Cards**: Fade in from bottom with stagger delay
2. **Expert Badge**: Pulse animation (scale 1.0 → 1.1)
3. **Hover**: Card lifts up with enhanced shadow
4. **Modal**: Slide in from center with scale effect

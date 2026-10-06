// Purpose: Renders the Group Card Skeleton interface within apps\web\src\components\common\jsx.
import '../css/Skeleton.css';

export default function GroupCardSkeleton() {
  return (
    <div className="group-card-skeleton">
      <div className="skel-header skeleton-shimmer" />
      <div className="skel-members">
        {Array.from({ length: 3 }, (_, i) => (
          <div key={i} className="skel-avatar skeleton-shimmer" />
        ))}
      </div>
      <div className="skel-stats skeleton-shimmer" />
    </div>
  );
}

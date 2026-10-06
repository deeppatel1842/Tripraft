// Purpose: Renders the Page Skeleton interface within apps\web\src\components\common\jsx.
import '../css/Skeleton.css';

export default function PageSkeleton() {
  return (
    <div className="page-skeleton">
      <div className="page-skeleton-header skeleton-shimmer" />
      <div className="page-skeleton-subtitle skeleton-shimmer" />
      <div className="page-skeleton-grid">
        {Array.from({ length: 6 }, (_, i) => (
          <div key={i} className="page-skeleton-card skeleton-shimmer" />
        ))}
      </div>
    </div>
  );
}

import '../css/Skeleton.css';

export default function PlaceCardSkeleton() {
  return (
    <div className="place-card-skeleton">
      <div className="skel-image skeleton-shimmer" />
      <div className="skel-body">
        <div className="skel-title skeleton-shimmer" />
        <div className="skel-subtitle skeleton-shimmer" />
        <div className="skel-rating skeleton-shimmer" />
      </div>
    </div>
  );
}

import {useSortable} from '@dnd-kit/sortable';
import {CSS} from '@dnd-kit/utilities';
import {StopwatchItem} from "./StopwatchItem";


export function SortableStopwatchItem({item, isFuture, onEdit, onStart, onStop, onReset, onDelete, activeId, runningId, getElapsed, formatTimeString, CircularProgress, CircularProgressTotal}){
    
     const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
    } = useSortable({id: item.id});
  
    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: activeId === item.id ? 0.3 : 1, // Dim dragged item
    };
    
    return (
        <div ref={setNodeRef} style={style} {...attributes} className={`sortable-stopwatch-item${item.isTotal ? " total-stopwatch-wrapper" : ""}`}>
          <StopwatchItem
            item={item}
            isFuture={isFuture}
            onEdit={onEdit}
            onStart = {onStart}
            onStop = {onStop}
            onReset = {onReset}
            onDelete= {onDelete}
            runningId = {runningId}
            getElapsed = {getElapsed}
            formatTimeString = {formatTimeString}
            CircularProgress = {CircularProgress}
            CircularProgressTotal = {CircularProgressTotal}
            listeners = {listeners}
          />
      </div>
    );
}
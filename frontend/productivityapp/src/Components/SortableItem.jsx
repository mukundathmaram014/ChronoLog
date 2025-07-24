import {useSortable} from '@dnd-kit/sortable';
import {CSS} from '@dnd-kit/utilities';
import {HabitItem} from "./HabitItem";

export function SortableItem({item, isFuture, onEdit, onDelete, onToggle, activeId}){
    
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
        <div ref={setNodeRef} style={style} {...attributes}>
          <HabitItem
            item={item}
            isFuture={isFuture}
            onEdit={onEdit}
            onDelete={onDelete}
            onToggle={onToggle}
            listeners = {listeners}
          />
      </div>

    );
}
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Bookmark, BookmarkCheck } from "lucide-react";
import { changeSavedStatus } from "./api";

type SaveButtonProps = {
  opportunityId: string;
  isSaved: boolean;
  disabled?: boolean;
};

export default function SaveButton({
  opportunityId,
  isSaved,
  disabled = false,
}: SaveButtonProps) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => changeSavedStatus(opportunityId, isSaved),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["saved-opportunity-ids"] }),
        queryClient.invalidateQueries({ queryKey: ["opportunities"] }),
      ]);
    },
  });

  return (
    <div className="save-control">
      <button
        className="save-button"
        type="button"
        aria-pressed={isSaved}
        disabled={disabled || mutation.isPending}
        onClick={() => mutation.mutate()}
      >
        {isSaved
          ? <BookmarkCheck size={16} aria-hidden="true" />
          : <Bookmark size={16} aria-hidden="true" />}
        {mutation.isPending
          ? "Saving…"
          : isSaved ? "Saved" : "Save"}
      </button>
      {mutation.isError && (
        <span className="save-error" role="status">
          {mutation.error instanceof Error
            ? mutation.error.message
            : "Could not update saved opportunities."}
        </span>
      )}
    </div>
  );
}
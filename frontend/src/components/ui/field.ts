/**
 * Form controls. Inputs stay white with a control-weight edge and turn ink on focus. Text is 16px on
 * phones so iOS does not zoom the page, 14px from the small breakpoint up.
 */
const CONTROL =
  'w-full rounded-md border border-edge bg-sheet text-base text-ink outline-none transition-colors duration-150 ' +
  'placeholder:text-pencil focus:border-ink focus:ring-1 focus:ring-ink disabled:cursor-not-allowed disabled:opacity-60 sm:text-sm'

export const inputClass = `${CONTROL} h-10 px-3`

export const textareaClass = `${CONTROL} px-3 py-2.5 leading-relaxed`

export const labelClass = 'flex flex-col gap-2 text-sm font-medium text-ink'

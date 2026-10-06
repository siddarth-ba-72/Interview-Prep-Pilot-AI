import type { LucideIcon } from 'lucide-react'
import { ClipboardCheck, Gauge, LayoutDashboard, MessagesSquare, Mic, UserPlus } from 'lucide-react'

/**
 * Everything the "How it works" page says. The screenshots live in public/how-it-works/{light,dark}/
 * and are re-taken with `node e2e/demo/capture-how-it-works.mjs` (see that script for how to run it).
 * Limit numbers mirror `usage-limits` in topic-service's application.yml; keep them in step.
 */

export type ShotName =
  | 'sign-in'
  | 'register'
  | 'onboarding'
  | 'profile'
  | 'dashboard-empty'
  | 'dashboard-topic'
  | 'learn-start'
  | 'learn-lesson'
  | 'learn-followup'
  | 'learn-guardrail'
  | 'test-questions'
  | 'test-written'
  | 'test-results'
  | 'test-report'
  | 'test-history'
  | 'test-retest'
  | 'interview-setup'
  | 'interview-question'
  | 'interview-feedback'
  | 'interview-needs-work'
  | 'interview-report'
  | 'interview-model-answers'
  | 'interview-revisit'
  | 'interview-history'
  | 'limits-dashboard'
  | 'limits-interview'

export function shotUrl(shot: ShotName, theme: 'light' | 'dark'): string {
  return `/how-it-works/${theme}/${shot}.webp`
}

/** A labelled marker on a screenshot; x and y are percentages of its width and height. */
export interface Hotspot {
  x: number
  y: number
  label: string
}

export interface Scene {
  title: string
  body: string
  shot: ShotName
  /** Where to find this screen in the app, shown in the frame's address bar. */
  where: string
  hotspots?: Hotspot[]
}

export interface Step {
  id: string
  nav: string
  /** A few words for the journey strip at the top of the page. */
  summary: string
  icon: LucideIcon
  title: string
  lead: string
  scenes: Scene[]
  tips: string[]
}

export const STEPS: Step[] = [
  {
    id: 'get-started',
    nav: 'Get started',
    summary: 'Sign up and set your level',
    icon: UserPlus,
    title: 'Create your account and tell us about yourself',
    lead: 'It takes under a minute. Your answers decide how hard your lessons, tests and interviews are.',
    scenes: [
      {
        title: 'Sign in or sign up',
        body: 'Use your email and password, or sign in with Google in one click.',
        shot: 'sign-in',
        where: 'Sign in',
      },
      {
        title: 'Register with your email',
        body: 'New here? Pick a display name, add your email and choose a password.',
        shot: 'register',
        where: 'Register',
      },
      {
        title: 'Answer two quick questions',
        body: 'Choose your domain, like Frontend, Backend or Data science, and your experience. Pick College student if you are preparing for campus placements.',
        shot: 'onboarding',
        where: 'Onboarding',
        hotspots: [
          { x: 60, y: 55.7, label: 'Preparing for placements? Pick this' },
          { x: 60, y: 84.5, label: 'Content pitched at your level' },
        ],
      },
      {
        title: 'Change it any time',
        body: 'Your answers live under Profile on the dashboard. Update them whenever your goals change.',
        shot: 'profile',
        where: 'Dashboard › Profile',
      },
    ],
    tips: [
      'Choosing College student focuses Learn and Test Mode on what campus placements ask, and pitches mock interviews at student level.',
      'Your topics, chats and reports are private. Only you can see them.',
    ],
  },
  {
    id: 'dashboard',
    nav: 'Dashboard',
    summary: 'Add the topics you need',
    icon: LayoutDashboard,
    title: 'Add the topics you want to master',
    lead: 'Everything starts with a topic. Add the subjects you are preparing for, then practise each one in three ways.',
    scenes: [
      {
        title: 'Meet your dashboard',
        body: 'Your topics and your daily usage live here. The tiles at the top show what you have left for today.',
        shot: 'dashboard-empty',
        where: 'Dashboard',
        hotspots: [
          { x: 33.5, y: 31, label: 'What you have left today' },
          { x: 87, y: 43.8, label: 'Add a topic here' },
        ],
      },
      {
        title: 'Add a topic',
        body: 'Type any subject, like Python, DBMS, Operating Systems or React, and press Add Topic. Each topic gets its own card.',
        shot: 'dashboard-topic',
        where: 'Dashboard',
        hotspots: [{ x: 26.5, y: 73, label: 'Learn, Test or Mock Interview' }],
      },
    ],
    tips: [
      'Every topic card has Learn, Test and Mock Interview buttons, plus links to its test and interview history.',
      'Once you take tests, the card shows your average score, so you can see your progress at a glance.',
    ],
  },
  {
    id: 'learn',
    nav: 'Learn',
    summary: 'Chat with your AI tutor',
    icon: MessagesSquare,
    title: 'Learn Mode: your personal AI tutor',
    lead: 'Chat about the topic, ask anything, and go as deep as you need. It is like having a senior who never gets tired of your questions.',
    scenes: [
      {
        title: 'The tutor gets to know you',
        body: 'Before teaching, it asks how much you already know, whether you want quick revision notes or a deep dive, and what you are preparing for.',
        shot: 'learn-start',
        where: 'Python › Learn',
      },
      {
        title: 'Get a structured lesson',
        body: 'Answers appear as they are written, with headings, examples and code, focused on what interviewers actually ask.',
        shot: 'learn-lesson',
        where: 'Python › Learn',
      },
      {
        title: 'Ask follow-up questions',
        body: 'Ask for an example, a simpler explanation or more depth. The tutor remembers the whole conversation.',
        shot: 'learn-followup',
        where: 'Python › Learn',
        hotspots: [{ x: 34.5, y: 88.7, label: 'Messages left today' }],
      },
      {
        title: 'It stays on topic',
        body: 'Off-topic questions get a polite nudge back to your preparation, so your messages go where they count.',
        shot: 'learn-guardrail',
        where: 'Python › Learn',
      },
    ],
    tips: [
      'One chat per topic, saved automatically. Leave any time and pick up exactly where you left off.',
      'Each message you send uses one Learn message. The tutor’s first reply in a new chat is free.',
    ],
  },
  {
    id: 'test',
    nav: 'Test',
    summary: 'Take a 20-question test',
    icon: ClipboardCheck,
    title: 'Test Mode: find out what you really know',
    lead: 'Every test is freshly written for your topic and level, then graded by AI with feedback on every answer.',
    scenes: [
      {
        title: 'A fresh 20-question test',
        body: '10 multiple-choice and 10 written questions covering concepts, scenarios and code. It is ready in a few seconds.',
        shot: 'test-questions',
        where: 'Python › Test',
        hotspots: [{ x: 38, y: 19.3, label: 'Your progress' }],
      },
      {
        title: 'Write your answers',
        body: 'Explain written answers in your own words. They are graded against a model answer, so your reasoning counts.',
        shot: 'test-written',
        where: 'Python › Test',
      },
      {
        title: 'Instant results',
        body: 'Submit and see your score straight away, next to your average across all attempts.',
        shot: 'test-results',
        where: 'Python › Test',
      },
      {
        title: 'A detailed report',
        body: 'See your strengths, the areas to improve, and every question with your answer, the correct answer and feedback.',
        shot: 'test-report',
        where: 'Python › Test history › Report',
      },
      {
        title: 'Every attempt is saved',
        body: 'Test history keeps every report. Open any of them again whenever you like.',
        shot: 'test-history',
        where: 'Python › Test history',
      },
      {
        title: 'Retest your weak spots',
        body: 'Start a new test from history and it focuses on the areas you got wrong last time.',
        shot: 'test-retest',
        where: 'Python › Test',
        hotspots: [{ x: 54.8, y: 13.5, label: 'Built from your last attempt' }],
      },
    ],
    tips: [
      'Not sure of an answer? Leave it blank. A wrong answer costs marks, a blank one costs nothing.',
      'Read the report before your next attempt: the retest is built from your weak areas.',
    ],
  },
  {
    id: 'interview',
    nav: 'Interview',
    summary: 'Practise a timed interview',
    icon: Mic,
    title: 'Mock Interview: the closest thing to the real one',
    lead: 'One question at a time, on a real clock, with feedback after every answer and a full report at the end.',
    scenes: [
      {
        title: 'Set up your interview',
        body: 'Pick how long you want to practise: 30, 45 or 60 minutes. As a student, your level and difficulty are set for you.',
        shot: 'interview-setup',
        where: 'Python › Mock Interview',
        hotspots: [{ x: 78.5, y: 60.6, label: 'Choose a duration' }],
      },
      {
        title: 'Answer one question at a time',
        body: 'Type your answer the way you would say it out loud. The timer keeps running, just like in a real interview.',
        shot: 'interview-question',
        where: 'Python › Mock Interview',
        hotspots: [{ x: 20.6, y: 11.4, label: 'The clock never pauses' }],
      },
      {
        title: 'Feedback after every answer',
        body: 'Each answer is rated Strong, Satisfactory or Needs work, with what was good and what to add.',
        shot: 'interview-feedback',
        where: 'Python › Mock Interview',
      },
      {
        title: 'Honest about weak answers',
        body: 'A vague answer is called out, along with what a good answer would have covered.',
        shot: 'interview-needs-work',
        where: 'Python › Mock Interview',
      },
      {
        title: 'Your interview report',
        body: 'End whenever you like, or when time runs out. You get a score out of 100, an overall assessment, your strengths and the areas to improve.',
        shot: 'interview-report',
        where: 'Python › Interview history › Report',
        hotspots: [{ x: 34, y: 14, label: 'Score and verdict' }],
      },
      {
        title: 'Learn from model answers',
        body: 'For the questions you struggled with, see how a stronger candidate would have answered.',
        shot: 'interview-model-answers',
        where: 'Python › Interview history › Report',
      },
      {
        title: 'Revisit your weak areas',
        body: 'Revisit topic in Learn Mode takes you straight back to your tutor to work on what you missed.',
        shot: 'interview-revisit',
        where: 'Python › Interview history › Report',
      },
      {
        title: 'Interview history',
        body: 'Every interview is saved. Resume one that is still running, or reopen any report.',
        shot: 'interview-history',
        where: 'Python › Interview history',
      },
    ],
    tips: [
      'A strong answer can earn a follow-up question, just like a real interviewer digging deeper.',
      'Practise answering out loud as you type. It makes the real interview feel familiar.',
    ],
  },
]

export const LIMITS_STEP: Step = {
  id: 'limits',
  nav: 'Limits',
  summary: 'Know your daily limits',
  icon: Gauge,
  title: 'Daily limits, explained',
  lead: 'To keep PrepPilot fair for everyone, the AI-powered actions have daily limits. Here is how they work.',
  scenes: [
    {
      title: 'Check what you have left',
      body: 'The tiles on your dashboard always show how many uses you have left.',
      shot: 'dashboard-empty',
      where: 'Dashboard',
      hotspots: [{ x: 33.5, y: 31, label: 'What you have left today' }],
    },
    {
      title: 'When a limit is used up',
      body: 'The tile turns red and tells you exactly when that action comes back.',
      shot: 'limits-dashboard',
      where: 'Dashboard',
      hotspots: [{ x: 72, y: 27, label: 'Shows when it comes back' }],
    },
    {
      title: 'Everything else keeps working',
      body: 'A locked action says when you can use it again. Your chats, reports and history stay open.',
      shot: 'limits-interview',
      where: 'Python › Mock Interview',
      hotspots: [{ x: 59.5, y: 72.5, label: 'When you can start again' }],
    },
  ],
  tips: [],
}

export type LimitKey = 'topics' | 'learnMessages' | 'tests' | 'mockInterviews'

export const LIMIT_ACTIONS: Array<{ key: LimitKey; label: string; unit: string }> = [
  { key: 'topics', label: 'Topics', unit: 'at a time' },
  { key: 'learnMessages', label: 'Learn messages', unit: 'per 24 hours' },
  { key: 'tests', label: 'Tests', unit: 'per 24 hours' },
  { key: 'mockInterviews', label: 'Mock interviews', unit: 'per 24 hours' },
]

/** null means no limit. */
export const TIERS: Record<'student' | 'standard', { label: string; hint: string; limits: Record<LimitKey, number | null> }> = {
  student: {
    label: 'College students',
    hint: 'If you picked College student in your profile',
    limits: { topics: 2, learnMessages: 30, tests: 2, mockInterviews: 1 },
  },
  standard: {
    label: 'Everyone else',
    hint: 'Any other experience level',
    limits: { topics: null, learnMessages: 50, tests: 3, mockInterviews: 2 },
  },
}

export const COSTS_A_USE = ['Sending a message in Learn Mode', 'Starting a new test', 'Starting a new mock interview']

export const ALWAYS_FREE = [
  'The tutor’s first reply in a new chat',
  'Submitting a test and getting your report',
  'Answering questions and ending an interview',
  'Resuming a test or interview in progress',
  'Reading your chats, reports and history',
]

export const LEARN_PROMPTS = [
  'Explain decorators like I am seeing them for the first time',
  'Give me 5 questions interviewers ask about DBMS normalization',
  'Quiz me on Python lists vs tuples, one question at a time',
  'Show me a code example of binary search and its complexity',
  'What is the difference between a process and a thread?',
]

export const FAQS: Array<{ q: string; a: string }> = [
  {
    q: 'Where should I start: Learn, Test or Mock Interview?',
    a: 'Start in Learn Mode to build your understanding, take a test to see where you stand, then try a mock interview. After each report, use Revisit to study your weak areas, and repeat.',
  },
  {
    q: 'Which topics can I prepare?',
    a: 'Any technical topic: programming languages like Python or Java, CS fundamentals like DBMS, Operating Systems and Computer Networks, frameworks, system design and more.',
  },
  {
    q: 'Who can see my chats and reports?',
    a: 'Only you. Every topic, chat and report belongs to your account and nobody else can open it.',
  },
  {
    q: 'What happens when I reach a limit?',
    a: 'Only that action locks, and the app shows exactly when it comes back: 24 hours after your last use, with the full limit restored. You can still read your chats, reports and history.',
  },
  {
    q: 'What if the AI fails halfway?',
    a: 'If a Learn message, test or interview cannot be generated, the use is given back automatically, so you never lose a use to an error.',
  },
  {
    q: 'Will I lose my progress if I close the tab?',
    a: 'No. Chats, tests and reports are saved as you go. An unfinished interview can be resumed from the Mock Interview page, but its clock keeps running while you are away.',
  },
  {
    q: 'How is a test scored?',
    a: 'Multiple-choice answers score +1 if right and −1 if wrong. Written answers score +5 or −5. Blank answers score 0. The maximum is 60 and you pass at 36.',
  },
  {
    q: 'Can I change my experience level later?',
    a: 'Yes, open Profile on the dashboard. New lessons, tests and interviews use your updated answers.',
  },
]

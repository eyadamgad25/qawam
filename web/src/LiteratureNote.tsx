import { LITERATURE_LABEL_AR, type LiteratureSource } from './demoDefaults';

/** Marks a value as literature-derived and not physio-reviewed, with its source. */
export default function LiteratureNote({ source }: { source: LiteratureSource }) {
  return (
    <span className="literature-note">
      {LITERATURE_LABEL_AR}.{' '}
      <a href={source.url} target="_blank" rel="noreferrer" dir="ltr" lang="en">
        {source.citation}
      </a>
    </span>
  );
}

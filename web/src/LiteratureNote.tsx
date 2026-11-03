import {
  LITERATURE_LABEL_AR,
  LITERATURE_LABEL_EN,
  type LiteratureSource,
} from './demoDefaults';
import { tr } from './i18n';

/** Marks a value as literature-derived and not physio-reviewed, with its source. */
export default function LiteratureNote({ source }: { source: LiteratureSource }) {
  return (
    <span className="literature-note">
      {tr(LITERATURE_LABEL_AR, LITERATURE_LABEL_EN)}.{' '}
      <a href={source.url} target="_blank" rel="noreferrer" dir="ltr" lang="en">
        {source.citation}
      </a>
    </span>
  );
}

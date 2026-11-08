"use client";

import ActionCenter from "./ActionCenter";

export default function OverdueList(props: any) {
  return <ActionCenter items={props.items ?? []} businessName={props.businessName} />;
}

"""Cadence UI components."""

from __future__ import annotations


def glass_card(st, title=None, body=None):
    with st.container(border=True):
        if title:
            st.markdown(f"#### {title}")
        if body:
            st.write(body)


def stat_tile(st, label, value):
    with st.container(border=True):
        st.caption(label)
        st.markdown(f"**{value}**")


def phase_heart(st, phase, saved=False):
    with st.container(border=True):
        st.caption(phase)
        st.markdown("&#9829;" if saved else "&#9825;", unsafe_allow_html=True)


def safety_banner(st, alerts):
    if not alerts:
        return
    st.error("Please consider contacting a clinician. Plans are suppressed for this check-in.")
    for alert in alerts:
        st.write(f"- {alert}")

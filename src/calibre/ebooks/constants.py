#!/usr/bin/env python
# vim:fileencoding=utf-8


__license__ = 'GPL v3'
__copyright__ = '2014, Kovid Goyal <kovid at kovidgoyal.net>'

html5_tags = (  # {{{
frozenset('''\
html
head
title
base
link
meta
style
script
noscript
body
section
nav
article
aside
h1
h2
h3
h4
h5
h6
header
footer
address
p
hr
br
pre
dialog
blockquote
ol
ul
li
dl
dt
dd
a
q
cite
em
strong
small
mark
dfn
abbr
time
progress
meter
code
var
samp
kbd
sub
sup
span
i
b
bdo
ruby
rt
rp
ins
del
figure
img
iframe
embed
object
param
video
audio
source
canvas
map
area
table
caption
colgroup
col
tbody
thead
tfoot
tr
td
th
form
fieldset
label
input
button
select
datalist
optgroup
option
textarea
output
details
command
bb
menu
legend
div'''.splitlines()))  # }}}

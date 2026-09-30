-- lab.lua: adds the animated hero banner (from the page's `hero:` metadata)
-- and a shared footer (from _lab.yml) to every page.

local function s(v)
  if v == nil then return "" end
  return pandoc.utils.stringify(v)
end

local function esc(t)
  return (t:gsub("&", "&amp;"):gsub("<", "&lt;"):gsub(">", "&gt;"):gsub('"', "&quot;"))
end

function Pandoc(doc)
  local meta = doc.meta
  local lab = meta.lab or {}
  local hero = meta.hero

  if hero then
    local html = {'<section class="hero-banner"><div class="hero-frame" id="hero-animation"></div><div class="hero-overlay">'}
    if hero.logo then
      table.insert(html, '<img class="hero-logo" src="' .. esc(s(hero.logo)) .. '" alt="' .. esc(s(lab.name)) .. '">')
    end
    if hero.title then
      table.insert(html, '<div class="hero-title">' .. esc(s(hero.title)) .. '</div>')
    end
    if hero.subtitle then
      table.insert(html, '<div class="hero-subtitle">' .. esc(s(hero.subtitle)) .. '</div>')
    end
    if hero.institution then
      table.insert(html, '<div class="hero-institution">' .. esc(s(lab.institution)) .. '</div>')
    end
    table.insert(html, '</div></section>')
    table.insert(doc.blocks, 1, pandoc.RawBlock("html", table.concat(html)))
  end

  -- footer
  local year = os.date("%Y")
  local lines = {}
  for _, k in ipairs({"department", "address"}) do
    local v = s(lab[k])
    if v ~= "" then table.insert(lines, esc(v)) end
  end
  local email = s(lab.email)
  local footer = '<footer class="lab-footer"><div class="lab-footer-inner">'
    .. '<div class="lab-footer-left"><img src="images/uw-logo-white.png" alt="' .. esc(s(lab.institution)) .. '" class="footer-uw"></div>'
    .. '<div class="lab-footer-right"><div class="footer-name">' .. esc(s(lab.name)) .. '</div>'
    .. '<div class="footer-full">' .. esc(s(lab.full_name)) .. '</div>'
    .. '<div class="footer-lines">' .. table.concat(lines, "<br>") .. '</div>'
  if email ~= "" then
    footer = footer .. '<div class="footer-email"><a href="mailto:' .. esc(email) .. '">' .. esc(email) .. '</a></div>'
  end
  footer = footer .. '</div></div><div class="footer-copy">© ' .. year .. ' ' .. esc(s(lab.name)) .. ' · Built with Quarto, special thanks to <a href="https://zaporski-lab.github.io" target="_blank" rel="noopener">Zaporski Lab</a></div></footer>'
  table.insert(doc.blocks, pandoc.RawBlock("html", footer))
  return doc
end

library ieee; use ieee.std_logic_1164.all;
entity e5 is port (a, b : in std_ulogic; q : out std_ulogic); end entity;
architecture x of e5 is
  function pick (s, u : std_ulogic) return std_ulogic is
  begin
    if s = '1' then return u; else return '0'; end if;
  end function pick;
begin
  q <= pick(a, b);
end architecture;

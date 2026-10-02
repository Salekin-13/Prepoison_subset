library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
entity d6 is port (a : in std_ulogic; q : out std_ulogic); end entity;
architecture x of d6 is
  function f (i : std_ulogic) return std_ulogic is
    variable t : std_ulogic;
  begin
    t := not i;
    return t;
  end function f;
  signal s_after : std_ulogic;
begin
  s_after <= f(a); q <= s_after;
end architecture;

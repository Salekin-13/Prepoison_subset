library ieee; use ieee.std_logic_1164.all;
entity c3 is port (sel : in std_ulogic_vector(1 downto 0); a, b : in std_ulogic; q : out std_ulogic); end entity;
architecture x of c3 is begin
  case sel is
    when "00" => q <= a;
    when others => q <= b;
  end case;
end architecture;

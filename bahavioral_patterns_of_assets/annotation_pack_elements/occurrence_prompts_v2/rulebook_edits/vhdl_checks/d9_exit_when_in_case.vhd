library ieee; use ieee.std_logic_1164.all;
entity d9 is port (clk : in std_ulogic; sel : in std_ulogic_vector(1 downto 0); q : out std_ulogic); end entity;
architecture x of d9 is begin
  p: process (clk)
  begin
    if rising_edge(clk) then
      case sel is
        when "00" =>
          for i in 0 to 3 loop
            exit when i = 2;
            q <= '1';
          end loop;
        when others =>
          q <= '0';
      end case;
    end if;
  end process p;
end architecture;
